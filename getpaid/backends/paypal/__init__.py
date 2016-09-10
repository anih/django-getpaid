import datetime
import logging
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from getpaid.models import Payment
from paypal.standard.conf import SANDBOX_POSTBACK_ENDPOINT, POSTBACK_ENDPOINT
from paypal.standard.forms import PayPalPaymentsForm
from paypal.standard.models import ST_PP_COMPLETED, ST_PP_DENIED, ST_PP_REFUSED, ST_PP_CANCELLED
from paypal.standard.ipn.signals import valid_ipn_received

from getpaid import signals
from getpaid.backends import PaymentProcessorBase
from getpaid.utils import get_domain

logger = logging.getLogger('getpaid.backends.paypal')


class PaymentProcessor(PaymentProcessorBase):
    BACKEND = 'getpaid.backends.paypal'
    BACKEND_NAME = _('paypal')
    BACKEND_ACCEPTED_CURRENCY = ('PLN', 'USD', 'EUR', 'GPB')
    BACKEND_LOGO_URL = 'getpaid/backends/paypal/paypal_logo.png'

    @staticmethod
    def ipn_signal_handler(sender, **kwargs):
        ipn_obj = sender
        payment = Payment.objects.get(pk=ipn_obj.custom)
        payment.external_id = ipn_obj.txn_id
        payment.description = ipn_obj.item_name

        if ipn_obj.payment_status == ST_PP_COMPLETED:
            business = PaymentProcessor.get_business()
            if ipn_obj.receiver_email != business:
                # Not a valid payment
                return

            payment.amount_paid = Decimal(ipn_obj.mc_gross)
            payment.paid_on = datetime.datetime.utcnow().replace(tzinfo=utc)
            payment.save()
            if Decimal(ipn_obj.mc_gross) >= payment.amount:
                logger.debug('paypal: status PAID')
                payment.change_status('paid')
            else:
                payment.change_status('partially_paid')

        elif ipn_obj.payment_status in (ST_PP_CANCELLED,
                                        ST_PP_DENIED,
                                        ST_PP_REFUSED):
            logger.debug('paypal: status FAILED')
            payment.save()
            payment.change_status('failed')
        else:
            logger.error('paypal: unknown status %d' % ipn_obj.payment_status)

    def get_return_url(self, type, pk=None):
        kwargs = {'pk': pk} if pk else {}
        url = reverse('getpaid-paypal-%s' % type, kwargs=kwargs)
        domain = get_domain()
        if PaymentProcessor.get_backend_setting('force_ssl', False):
            return 'https://%s%s' % (domain, url)
        else:
            return 'http://%s%s' % (domain, url)

    @staticmethod
    def is_test_mode():
        return getattr(settings, 'PAYPAL_TEST', True)

    @property
    def _get_gateway_url(self):
        return SANDBOX_POSTBACK_ENDPOINT if self.is_test_mode() else POSTBACK_ENDPOINT

    @staticmethod
    def get_business():
        if PaymentProcessor.is_test_mode():
            return PaymentProcessor.get_backend_setting('test_business')
        return PaymentProcessor.get_backend_setting('business')

    def get_gateway_url(self, request):
        """
        Routes a payment to Gateway, should return URL for redirection.

        """

        user_data = {
            'email': None,
            'lang': None,
            'first_name': None,
            'last_name': None,
        }

        signals.user_data_query.send(sender=None, order=self.payment.order, user_data=user_data)
        paypal_dict = {
            "business": self.get_business(),
            "amount": self.payment.amount,
            'currency_code': self.payment.currency.upper(),
            'item_name': self.get_order_description(self.payment, self.payment.order),
            # "invoice": "unique-invoice-id",
            "notify_url": self.get_return_url('online'),
            "return_url": self.get_return_url('success', self.payment.pk),
            "return": self.get_return_url('success', self.payment.pk),
            'cancel_return': self.get_return_url('failure', self.payment.pk),
            'custom': self.payment.pk,
        }
        return self._get_gateway_url, 'POST', paypal_dict

    def get_form(self, post_data):
        return PayPalPaymentsForm(initial=post_data)



#
# def show_me_the_money(sender, **kwargs):
#     ipn_obj = sender
#     if ipn_obj.payment_status == ST_PP_COMPLETED:
#         # WARNING !
#         # Check that the receiver email is the same we previously
#         # set on the business field request. (The user could tamper
#         # with those fields on payment form before send it to PayPal)
#         if ipn_obj.receiver_email != "receiver_email@example.com":
#             # Not a valid payment
#             return
#
#         # ALSO: for the same reason, you need to check the amount
#         # received etc. are all what you expect.
#
#         # Undertake some action depending upon `ipn_obj`.
#         if ipn_obj.custom == "Upgrade all users!":
#             Users.objects.update(paid=True)
#     else:

valid_ipn_received.connect(PaymentProcessor.ipn_signal_handler)
