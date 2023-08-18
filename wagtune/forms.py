from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.models import Page

from .utils import close_ab_test, create_ab_test, disable_auto_redirect


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

    def create_ab_test(self, original_page_pk, user):
        variant_count = int(self.cleaned_data['variant_count'])
        end_date = self.cleaned_data.get('end_date')

        return create_ab_test(original_page_pk, variant_count, end_date, user)


class EndABTestForm(forms.Form):
    confirmation = forms.BooleanField(required=True)

    def end_ab_test(self, variant_page_pk, user):
        return close_ab_test(variant_page_pk, closer_user=user)
