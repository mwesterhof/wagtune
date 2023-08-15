from collections import defaultdict
import json

from django.template import Library
from wagtail.models import Page

from wagtune.models import ABTestPage
from wagtune.utils import token_processor


register = Library()

@register.filter
def to_json(data):
    return json.dumps(data)


@register.inclusion_tag('wagtune/tags/overall_stat_table.html')
def overall_stat_table(instance):
    return {'stats': instance.overall_stats}


@register.inclusion_tag('wagtune/tags/overall_stat_graph.html')
def overall_stat_graph(instance):
    return {'stats': instance.overall_stats}


def get_hook_stats_for_page(instance):
    def _get_stats_for_variant(variant_id, variant_data, highest_day):
        variant = Page.objects.get(pk=variant_id)
        stats = [0 for _ in  range(highest_day+1)]
        revisions = [0 for _ in range(highest_day+1)]

        for revision_id, day_data in variant_data.items():
            revision_id = int(revision_id)
            for day, hits in day_data.items():
                day = int(day)
                stats[day] += hits
                if revision_id > revisions[day]:
                    revisions[day] = revision_id

        hit_accumulated = 0
        for i, hits in enumerate(stats):
            hit_accumulated += hits
            stats[i] = hit_accumulated

        previous_revision = 0
        for i, revision in enumerate(revisions):
            if not revision:
                revisions[i] = previous_revision
            else:
                previous_revision = revision

        return {
            'variant': variant.title,
            'stats': stats,
            'revisions': revisions,
        }

    def _get_stats_for_hook(data, highest_day):
        return [
            _get_stats_for_variant(int(variant_id), variant_data, highest_day)
            for variant_id, variant_data in data.items()
        ]

    def _get_highest_day(data):
        highest_day = 0
        for _, hook_data in data.items():
            for _, variant_data in hook_data.items():
                for _, revision_data in variant_data.items():
                    highest_revision_day = max([int(day) for day in revision_data.keys()])
                    if highest_revision_day > highest_day:
                        highest_day = highest_revision_day

        return highest_day

    data = instance.statistics
    highest_day = _get_highest_day(data)
    gathered_stats = dict([
        (hook_name, _get_stats_for_hook(hook_data, highest_day))
        for hook_name, hook_data in data.items()
    ])

    return gathered_stats, highest_day


@register.inclusion_tag('wagtune/tags/hook_stat_graphs.html')
def hook_stat_graphs(instance):
    gathered_stats, highest_day = get_hook_stats_for_page(instance)

    return {
        'stats': gathered_stats,
        'highest_day': highest_day,
    }


@register.inclusion_tag('wagtune/tags/hook_stat_tables.html')
def hook_stat_tables(instance):
    if not instance.statistics:
        return {}

    gathered_stats, highest_day = get_hook_stats_for_page(instance)

    return {
        'stats': gathered_stats,
        'highest_day': highest_day,
    }


@register.inclusion_tag('wagtune/tags/provide_info.html', takes_context=True)
def provide_info(context):
    page = context.get('page')
    if not page:
        return context

    parent = page.get_parent().specific
    if not isinstance(parent, ABTestPage):
        return context

    token = token_processor.generate_token(parent.pk, page.pk, page.live_revision_id)
    context['abtest_token'] = token
    return context


@register.filter
def do_sum(values):
    return sum(values)
