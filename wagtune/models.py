from collections import defaultdict

from django.conf import settings
from django.db import models
from django.http import Http404
from django.utils.functional import cached_property
from django.utils.timezone import now

from wagtail.admin.panels import HelpPanel, FieldPanel
from wagtail.models import Page

from .utils import get_randomized_for_seed


class ABTestPage(Page):
    start_date = models.DateTimeField(auto_now_add=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    end_date = models.DateField(null=True, blank=True)
    statistics = models.JSONField(null=True, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('end_date'),
        HelpPanel(template='admin/panels/abtest_page_help.html'),
    ]

    @property
    def current_day(self):
        return (now() - self.start_date).days

    @cached_property
    def test_variants(self):
        return self.get_children().live().specific()

    @cached_property
    def hits_per_variant(self):
        variant_hits = defaultdict(int)
        for hook, hook_stats in self.statistics.items():
            for variant_id, variant_stats in hook_stats.items():
                for revision_id, revision_stats in variant_stats.items():
                    variant_hits[variant_id] += sum([hits for (day, hits) in revision_stats.items()])

        return variant_hits

    @cached_property
    def overall_stats(self):
        if not self.statistics:
            return []

        results = self.hits_per_variant
        stats = [
            (Page.objects.get(pk=pk).title, hits)
            for pk, hits in results.items()
        ]

        return stats

    @cached_property
    def best_scoring_variant(self):
        # if no data exists, always fall back to original
        if not self.statistics:
            return self.get_original_page()

        hits = self.hits_per_variant
        variant_id = sorted(hits.keys(), key=lambda k: hits[k], reverse=True)[0]
        return Page.objects.get(pk=variant_id)

    def get_preview_template(self, request, mode_name):
        return 'wagtune/abtest_preview.html'

    def get_delegated_page(self, request):
        visitor_key = request.session.get('visitorKey')
        randomized_value = get_randomized_for_seed(visitor_key, self.pk, 0, self.test_variants.count()-1)
        return self.test_variants[randomized_value]

    def get_original_page(self):
        return self.get_children().first()

    def serve(self, request, *args, **kwargs):
        return self.get_delegated_page(request).serve(request, *args, **kwargs)

    def route(self, request, path_components):
        if path_components:
            try:
                return self.get_original_page().route(request, path_components)
            except Http404:
                if path_components[0] != self.get_original_page().slug:
                    raise
                return self.get_original_page().route(request, path_components[1:])
        else:
            return super().route(request, path_components)
