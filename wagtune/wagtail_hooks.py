from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin import widgets as wagtailadmin_widgets
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import ABTestPage
from .views import CreateABTestView, EndABTestView, InspectABTestView


class ABTestPageAdmin(ModelAdmin):
    model = ABTestPage
    inspect_view_enabled = True
    inspect_view_class = InspectABTestView


modeladmin_register(ABTestPageAdmin)


@hooks.register('register_page_listing_buttons')
def page_listing_buttons(page, page_perms, next_url=None):
    # TODO: check page perms
    if isinstance(page.specific, ABTestPage):
        return
    if isinstance(page.get_parent().specific, ABTestPage):
        return

    yield wagtailadmin_widgets.PageListingButton(
        _("Create A/B test"),
        reverse('create_ab_test', args=(page.pk,)),
        priority=45
    )


@hooks.register('register_admin_urls')
def register_abtest_urls():
    return [
        path('create-ab-test/<int:pk>/', CreateABTestView.as_view(), name='create_ab_test'),
        path('end-ab-test/<int:pk>/', EndABTestView.as_view(), name='end_ab_test'),
    ]
