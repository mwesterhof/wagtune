from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page

from .models import ABTestPage
from .utils import close_ab_test, disable_auto_redirect


class CreateABTestForm(forms.Form):
    end_date = forms.DateField(required=False, widget=forms.SelectDateWidget())
    variant_count = forms.ChoiceField(choices=[(value, value) for value in range(2, 5)])
    confirmation = forms.BooleanField(required=True)

    def clean_end_date(self):
        today = timezone.now().date()
        end_date = self.cleaned_data.get('end_date')
        if end_date and end_date < today:
            raise forms.ValidationError(_("Only future dates are supported"))
        return end_date

    @disable_auto_redirect
    @transaction.atomic
    def create_ab_test(self, original_page_pk, user):
        variant_count = int(self.cleaned_data['variant_count'])
        end_date = self.cleaned_data.get('end_date')

        original_page = Page.objects.get(pk=original_page_pk)
        original_page_slug = original_page.slug

        ab_test_page = original_page.add_sibling(
            instance=ABTestPage(
                title=original_page.title,
                end_date=end_date,
                started_by=user,
            ),
            pos='left'
        )
        ab_test_page.save()
        original_page = Page.objects.get(pk=original_page.pk)

        original_page.move(ab_test_page, 'last-child')

        original_page = Page.objects.get(pk=original_page.pk)
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

    # @transaction.atomic
    def end_ab_test(self, variant_page_pk, user):
        return close_ab_test(Page.objects.get(pk=variant_page_pk), closer_user=user)
