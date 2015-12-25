from django.conf.urls import url, include

from getpaid.utils import import_backend_modules
from getpaid.views import NewPaymentView, FallbackView

urlpatterns = [
    url(r'^new/payment/(?P<currency>[A-Z]{3})/$', NewPaymentView.as_view(), name='getpaid-new-payment'),
    url(r'^payment/success/(?P<pk>\d+)/$', FallbackView.as_view(success=True), name='getpaid-success-fallback'),
    url(r'^payment/failure/(?P<pk>\d+)$', FallbackView.as_view(success=False), name='getpaid-failure-fallback'),
]

for backend_name, urls in list(import_backend_modules('urls').items()):
    urlpatterns.append(url(r'^%s/' % backend_name, include(urls)))
