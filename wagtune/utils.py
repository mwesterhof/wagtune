import random
import os
from base64 import b64encode, b64decode
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from functools import wraps

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template import loader
from html2text import HTML2Text
from wagtail.contrib.redirects.signal_handlers import (
    autocreate_redirects_on_page_move,
    autocreate_redirects_on_slug_change,
)
from wagtail.models import Page
from wagtail.signals import page_slug_changed, post_page_move



def disable_auto_redirect(function):
    def disconnect_signals():
        post_page_move.disconnect(autocreate_redirects_on_page_move)
        page_slug_changed.disconnect(autocreate_redirects_on_slug_change)

    def connect_signals():
        post_page_move.connect(autocreate_redirects_on_page_move)
        page_slug_changed.connect(autocreate_redirects_on_slug_change)

    @wraps(function)
    def f(*args, **kwargs):
        disconnect_signals()
        result = function(*args, **kwargs)
        connect_signals()
        return result

    return f


def render_email_content(user, variant_page, ab_test_page, was_starter):
    template = loader.get_template('wagtune/email/closing_report.html')
    context = {
        'user': user,
        'ab_test_page': ab_test_page.specific,
        'was_starter': was_starter,
        'winning_variant': variant_page,
    }

    return template.render(context)


def send_report_email(user, variant_page, ab_test_page, was_starter):
    html_content = render_email_content(user, variant_page, ab_test_page, was_starter)
    text_content = HTML2Text().handle(html_content)

    message = EmailMultiAlternatives(
        subject=f"Closing report for test page \"{ab_test_page}\"",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html_content, 'text/html')
    message.send()


@disable_auto_redirect
# @transaction.atomic
def close_ab_test(variant_page, closer_user=None):
    ab_test_parent = variant_page.get_parent()

    new_slug = ab_test_parent.slug
    ab_test_parent.slug += '_'
    ab_test_parent.save()

    # don't just use refresh_from_db(), as this doesn't refresh the treebeard cache
    variant_page = Page.objects.get(pk=variant_page.pk)
    new_parent = ab_test_parent.get_parent()

    starter_user = ab_test_parent.specific.started_by
    was_original_variant = ab_test_parent.get_children().specific().first() == variant_page

    # send stat emails where possible
    if starter_user.email:
        send_report_email(starter_user, variant_page, ab_test_parent, was_starter=True)
    if closer_user and closer_user.email and closer_user != starter_user:
        send_report_email(closer_user, variant_page, ab_test_parent, was_starter=False)

    if not was_original_variant:
        original_variant = ab_test_parent.get_children().first()
        for child in original_variant.get_children():
            child.move(variant_page, 'last-child')

    variant_page.move(new_parent, 'last-child')
    variant_page = Page.objects.get(pk=variant_page.pk)

    variant_page.title = ab_test_parent.title
    variant_page.draft_title = ab_test_parent.draft_title
    variant_page.slug = new_slug

    variant_page.save()
    ab_test_parent.delete()
    return new_parent


# @transaction.atomic  # TODO: make sure url paths work with this transaction
def _close_ab_test(variant_page, closer_user=None):
    ab_test_parent = variant_page.get_parent()
    starter_user = ab_test_parent.specific.started_by
    was_original_variant = ab_test_parent.get_children().specific().first() == variant_page

    # send stat emails where possible
    if starter_user.email:
        send_report_email(starter_user, variant_page, ab_test_parent, was_starter=True)
    if closer_user and closer_user.email and closer_user != starter_user:
        send_report_email(closer_user, variant_page, ab_test_parent, was_starter=False)

    # move children of original variant, if necessary
    if not was_original_variant:
        original_variant = ab_test_parent.get_children().first()
        for child in original_variant.get_children():
            child.move(variant_page, 'last-child')
            child.refresh_from_db()
            child.set_url_path(variant_page)
            child.save()
        variant_page.refresh_from_db()

    # 1. move variant up in tree
    ab_test_slug = ab_test_parent.slug
    new_parent = ab_test_parent.get_parent()

    variant_page.move(ab_test_parent, 'left')
    variant_page.refresh_from_db()
    variant_page.title = variant_page.draft_title = ab_test_parent.title
    variant_page.save()

    # ab_test_parent.refresh_from_db()  # TODO: check if this is needed

    # 2. remove parent, including obsolete variants
    variant_page.slug = ab_test_slug
    variant_page.save()

    ab_test_parent.refresh_from_db()
    ab_test_parent.delete()

    variant_page.set_url_path(new_parent)
    variant_page.save()
    # 3. return new parent page of variant (formerly its grandparent)
    return new_parent


def get_randomized_for_seed(visitor_key, page_id=1, min_value=0, max_value=1024):
    seed = visitor_key * page_id
    local_random = random.Random()
    local_random.seed(seed)
    return local_random.randint(min_value, max_value)


class TokenProcessor:
    def __init__(self):
        key = os.urandom(32)
        self.iv = os.urandom(16)
        self.cipher = Cipher(algorithms.AES(key), modes.CBC(self.iv))

    def generate_token(self, abtest_parent_id, abtest_variant_id, abtest_revision_id):
        to_encrypt = bytes(f'{abtest_parent_id}:{abtest_variant_id}:{abtest_revision_id}'.ljust(32), 'utf-8')

        encryptor = self.cipher.encryptor()
        return str(
            b64encode(encryptor.update(to_encrypt) + encryptor.finalize()),
            'utf-8'
        )

    def unpack_token(self, token_encoded):
        token = b64decode(token_encoded)
        decryptor = self.cipher.decryptor()
        decrypted = decryptor.update(token) + decryptor.finalize()
        abtest_parent_id, abtest_variant_id, abtest_revision_id = str(decrypted, 'utf-8').split(':')

        return int(abtest_parent_id), int(abtest_variant_id), int(abtest_revision_id)


token_processor = TokenProcessor()
