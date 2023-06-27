from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import now
from django.views.generic import FormView
from wagtail.contrib.modeladmin.views import InspectView

from .forms import CreateABTestForm, EndABTestForm
from .models import ABTestPage
from .utils import token_processor


def ab_test_view(request):
    token = request.GET['token']
    hook = request.GET['hook']

    parent_id, variant_id, revision_id = token_processor.unpack_token(token)
    variant_id = str(variant_id)
    revision_id = str(revision_id)
    parent_page = ABTestPage.objects.get(pk=parent_id)
    test_day = str(parent_page.current_day)

    if not parent_page.statistics:
        parent_page.statistics = {}

    if hook not in parent_page.statistics:
        parent_page.statistics[hook] = {}

    if variant_id not in parent_page.statistics[hook]:
        parent_page.statistics[hook][variant_id] = {}

    if revision_id not in parent_page.statistics[hook][variant_id]:
        parent_page.statistics[hook][variant_id][revision_id] = {}

    if test_day not in parent_page.statistics[hook][variant_id][revision_id]:
        parent_page.statistics[hook][variant_id][revision_id][test_day] = 0

    parent_page.statistics[hook][variant_id][revision_id][test_day] += 1
    parent_page.save()

    return HttpResponse('')


class CreateABTestView(FormView):
    form_class = CreateABTestForm
    template_name = 'wagtune/admin/create_ab_test.html'

    def form_valid(self, form):
        original_page_pk = self.kwargs['pk']
        ab_test_page = form.create_ab_test(original_page_pk)
        return HttpResponseRedirect(reverse('wagtailadmin_explore', args=(ab_test_page.pk,)))


class EndABTestView(FormView):
    form_class = EndABTestForm
    template_name = 'wagtune/admin/end_ab_test.html'

    def form_valid(self, form):
        variant_pk = self.kwargs['pk']
        new_parent = form.end_ab_test(variant_pk)
        return HttpResponseRedirect(reverse('wagtailadmin_explore', args=(new_parent.pk,)))


class InspectABTestView(InspectView):
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        instance = context['instance']
        context.update({
            'test_day': (now() - instance.start_date).days + 1,
        })
        return context
