from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from wagtune.models import ABTestPage
from wagtune.utils import close_ab_test


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        for testpage in ABTestPage.objects.filter(end_date__lt=timezone.now()):
            close_ab_test(testpage.best_scoring_variant)
