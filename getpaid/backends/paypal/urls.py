from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt

from getpaid.backends.paypal.views import FailureView, OnlineView, SuccessView

urlpatterns = [
    url(r'^online/$', csrf_exempt(OnlineView.as_view()), name='getpaid-paypal-online'),
    url(r'^success/(?P<pk>\d+)/', csrf_exempt(SuccessView.as_view()), name='getpaid-paypal-success'),
    url(r'^failure/(?P<pk>\d+)/', csrf_exempt(FailureView.as_view()), name='getpaid-paypal-failure'),
]
