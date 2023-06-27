from django.urls import path

from .views import ab_test_view


urlpatterns = [
    path('abtest-report', ab_test_view, name='abtest_url'),
]
