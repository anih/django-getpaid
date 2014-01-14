import logging
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from getpaid.backends.paypal import PaymentProcessor
from getpaid.backends.paypal.forms import PayPalIPNForm
from getpaid.backends.paypal.models import PaymentPaypal
from getpaid.models import Payment


logger = logging.getLogger('getpaid.backends.paypal')

class OnlineView(View):


    """
    This View answers on paypal's online request that is acknowledge of payment
    status change.

    The most important logic of this view is delegated to ``PaymentProcessor.online()`` method
    """
    def post(self, request, *args, **kwargs):

        logger.debug("received post from paypal: %s" % str(dict(request.POST.copy())) )
        flag = None
        ipn_obj = None

        # Clean up the data as PayPal sends some weird values such as "N/A"
        data = request.POST.copy()
        date_fields = ('time_created', 'payment_date', 'next_payment_date', 'subscr_date', 'subscr_effective')
        for date_field in date_fields:
            if data.get(date_field) == 'N/A':
                del data[date_field]

        try:
            payment = Payment.objects.get(pk=data['custom'])
        except (ValueError, Payment.DoesNotExist):
            logger.error('Got message for non existing Payment, %s' % str(data))
            flag =  'PAYMENT ERR'

        if not flag:
            form = PayPalIPNForm(data)
            if form.is_valid():
                try:
                    ipn_obj = form.save(commit=False)
                except Exception, e:
                    flag = "Exception while processing. (%s)" % e
            else:
                flag = "Invalid form. (%s)" % form.errors

        if not flag:
            if ipn_obj is None:
                ipn_obj = PaymentPaypal()
            ipn_obj.initialize(request)

            status = PaymentProcessor.online(ipn_obj, flag, form, secure=request.GET['secret'] if request.is_secure() and 'secret' in request.GET else None)
        else:
            status = flag
        logger.debug( 'paypal payment status: %s' % status)
        return HttpResponse(status)

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
        logger.error("Payment %s failed on backend error %s" % (self.kwargs['pk'], self.kwargs['error']))
        return HttpResponseRedirect(reverse('getpaid-failure-fallback', kwargs={'pk': self.object.pk}))
