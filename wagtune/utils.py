import random
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from base64 import b64encode, b64decode

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from html2text import HTML2Text


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
        from_email=settings.EMAIL_FROM,
        to=[user.email],
    )
    message.attach_alternative(html_content, 'text/html')
    message.send()


def close_ab_test(variant_page, closer_user=None):
    ab_test_parent = variant_page.get_parent()
    starter_user = ab_test_parent.specific.started_by

    # send stat emails where possible
    if starter_user.email:
        send_report_email(starter_user, variant_page, ab_test_parent, was_starter=True)
    if closer_user and closer_user.email and closer_user != starter_user:
        send_report_email(closer_user, variant_page, ab_test_parent, was_starter=False)

    # 1. move variant up in tree
    ab_test_slug = ab_test_parent.slug
    new_parent = ab_test_parent.get_parent()

    variant_page.move(ab_test_parent, 'left')
    variant_page.refresh_from_db()
    variant_page.title = variant_page.draft_title = ab_test_parent.title
    variant_page.save()

    # 2. remove parent, including obsolete variants
    ab_test_parent.delete()
    variant_page.slug = ab_test_slug
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
