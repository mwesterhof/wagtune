from django import forms
from django.db import transaction
from wagtail.models import Page

from .models import ABTestPage


class CreateABTestForm(forms.Form):
    confirmation = forms.BooleanField(required=True)
    variant_count = forms.ChoiceField(choices=[(value, value) for value in range(1, 5)])

    @transaction.atomic
    def create_ab_test(self, original_page_pk):
        variant_count = int(self.cleaned_data['variant_count'])

        original_page = Page.objects.get(pk=original_page_pk)
        original_page_slug = original_page.slug

        ab_test_page = original_page.add_sibling(instance=ABTestPage(title=original_page.title), pos='left')
        ab_test_page.save()
        original_page.refresh_from_db()

        original_page.move(ab_test_page, 'last-child')

        original_page.refresh_from_db()
        original_page.title = original_page.draft_title = 'variant 1'
        original_page.slug = 'variant_1'
        original_page.save()

        ab_test_page.slug = original_page_slug
        ab_test_page.save()

        for i in range(2, variant_count + 1):
            variant = original_page.copy(
                recursive=False,
                keep_live=False,
                update_attrs={
                    'slug': f'variant_{i}',
                    'title': f'variant {i}',
                    'draft_title': f'variant {i}',
                }
            )
            variant.save()

        return ab_test_page


class EndABTestForm(forms.Form):
    confirmation = forms.BooleanField(required=True)

    @transaction.atomic
    def end_ab_test(self, variant_page_pk):
        # 1. move variant up in tree
        variant_page = Page.objects.get(pk=variant_page_pk)
        ab_test_parent = variant_page.get_parent()
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
