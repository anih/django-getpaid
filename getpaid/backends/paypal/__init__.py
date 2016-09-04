import datetime
import logging
import urllib
from decimal import Decimal

from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _

from getpaid import signals
from getpaid.backends import PaymentProcessorBase
from utils import get_domain

logger = logging.getLogger('getpaid.backends.paypal')


class paypalTransactionStatus:
    ST_PP_ACTIVE = 'Active'
    ST_PP_CANCELLED = 'Cancelled'
    ST_PP_CLEARED = 'Cleared'
    ST_PP_COMPLETED = 'Completed'
    ST_PP_DENIED = 'Denied'
    ST_PP_PAID = 'Paid'
    ST_PP_PENDING = 'Pending'
    ST_PP_PROCESSED = 'Processed'
    ST_PP_REFUSED = 'Refused'
    ST_PP_REVERSED = 'Reversed'
    ST_PP_REWARDED = 'Rewarded'
    ST_PP_UNCLAIMED = 'Unclaimed'
    ST_PP_UNCLEARED = 'Uncleared'


class PaymentProcessor(PaymentProcessorBase):
    BACKEND = 'getpaid.backends.paypal'
    BACKEND_NAME = _('paypal')
    BACKEND_ACCEPTED_CURRENCY = ('PLN', 'USD', 'EUR', 'GPB')
    BACKEND_LOGO_URL = 'getpaid/backends/paypal/paypal_logo.png'
    # API Endpoints.
    POSTBACK_ENDPOINT = "https://www.paypal.com/cgi-bin/webscr"
    SANDBOX_POSTBACK_ENDPOINT = "https://www.sandbox.paypal.com/cgi-bin/webscr"

    @staticmethod
    def online(ipn_obj, flag, form, secure):

        if flag is not None:
            ipn_obj.set_flag(flag)
        else:
            # Secrets should only be used over SSL.
            if secure:
                ipn_obj.verify_secret(form, secure)
            else:
                business = PaymentProcessor.get_backend_setting('business') if not PaymentProcessor.get_backend_setting(
                    'test') \
                    else PaymentProcessor.get_backend_setting('test_business')
                ipn_obj.verify(receiver_email=business)

        # if verification ended in error, return it:
        if ipn_obj.flag:
            return ipn_obj.flag_info

        payment = ipn_obj.payment
        payment.external_id = ipn_obj.txn_id
        payment.description = ipn_obj.item_name

        if ipn_obj.payment_status == paypalTransactionStatus.ST_PP_COMPLETED:
            payment.amount_paid = Decimal(ipn_obj.mc_gross)
            payment.paid_on = datetime.datetime.utcnow().replace(tzinfo=utc)
            if Decimal(ipn_obj.mc_gross) >= payment.amount:
                logger.debug('paypal: status PAID')
                payment.change_status('paid')
            else:
                payment.change_status('partially_paid')
        elif ipn_obj.payment_status in (paypalTransactionStatus.ST_PP_CANCELLED,
                                        paypalTransactionStatus.ST_PP_DENIED,
                                        paypalTransactionStatus.ST_PP_REFUSED):
            logger.debug('paypal: status FAILED')
            payment.change_status('failed')
        else:
            logger.error('paypal: unknown status %d' % ipn_obj.payment_status)

        return 'OK'

    def get_return_url(self, type, pk=None):
        kwargs = {'pk': pk} if pk else {}
        url = reverse('getpaid-paypal-%s' % type, kwargs=kwargs)
        domain = get_domain()
        if PaymentProcessor.get_backend_setting('force_ssl', False):
            return 'https://%s%s' % (domain, url)
        else:
            return 'http://%s%s' % (domain, url)

    @property
    def _get_gateway_url(cls):
        test = PaymentProcessor.get_backend_setting('test', True)
        return cls.SANDBOX_POSTBACK_ENDPOINT if test else cls.POSTBACK_ENDPOINT

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
        business = PaymentProcessor.get_backend_setting('business') if not PaymentProcessor.get_backend_setting(
            'test') \
            else PaymentProcessor.get_backend_setting('test_business')
        params = {
            'business': business,
            'cmd': "_xclick",
            'charset': "utf-8",
            'landing_page': request.REQUEST.get('landing_page', ''),
        }

        # transaction data
        # Here we put payment.pk as we can get order through payment model
        params['custom'] = self.payment.pk
        # total amount
        params['amount'] = self.payment.amount
        # currency
        params['currency_code'] = self.payment.currency.upper()
        # description
        params['item_name'] = self.get_order_description(self.payment, self.payment.order)
        # payment methods
        params['item_number'] = None
        # fast checkout
        params['payment_type'] = 'WLT'
        # quantity
        params['quantity'] = 1

        # urls
        # params['logo_url'] = PaymentProcessor.get_backend_setting('logo_url);
        params['return_url'] = self.get_return_url('success', self.payment.pk)
        params['cancel_return'] = self.get_return_url('failure', self.payment.pk)
        params['notify_url'] = self.get_return_url('online')
        logger.debug('sending payment to paypal: %s' % str(params))
        for key in params.keys():
            params[key] = unicode(params[key]).encode('utf-8')
        return self._get_gateway_url + '?' + urllib.urlencode(params), 'GET', {}
        # return self._get_gateway_url, 'POST', params
