import logging

from django.urls import reverse
from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from paypal.standard.ipn.views import ipn

from getpaid.models import Payment

logger = logging.getLogger('getpaid.backends.paypal')


class OnlineView(View):
    def post(self, request, *args, **kwargs):
        return ipn(request=request)


class SuccessView(DetailView):
    """
    This view just redirects to standard backend success link.
    """
    model = Payment

    def render_to_response(self, context, **response_kwargs):
        return HttpResponseRedirect(reverse('getpaid-success-fallback', kwargs={'pk': self.object.pk}))


class FailureView(DetailView):
    """
    This view just redirects to standard backend failure link.
    """
    model = Payment

    def render_to_response(self, context, **response_kwargs):
        logger.error("Payment %s failed on backend error %s" % (self.kwargs['pk'], 'user canceled'))
        self.object.change_status('canceled')
        return HttpResponseRedirect(reverse('getpaid-failure-fallback', kwargs={'pk': self.object.pk}))
