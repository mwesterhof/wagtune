from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError

from wagtune.models import ABTestPage


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        for page in ABTestPage.objects.all():
            page.start_date -= timedelta(days=1)
            page.save()
