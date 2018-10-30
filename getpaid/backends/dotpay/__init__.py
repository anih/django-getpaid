import datetime
from decimal import Decimal
import hashlib
import logging

from django import forms
from django.utils import six
from six.moves.urllib.parse import urlencode
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from getpaid import signals
from getpaid.backends import PaymentProcessorBase

logger = logging.getLogger('getpaid.backends.dotpay')


class DotpayTransactionStatus:
    STARTED = 'new'
    PROCESSING = 'processing'
    FINISHED = 'completed'
    REJECTED = 'rejected'


class PaymentProcessor(PaymentProcessorBase):

    configuration_options = {
        'id': forms.IntegerField(label='DotPay - ID sprzedawcy'),
        'PIN': forms.CharField(label='DotPay - PIN sprzedawcy'),
    }

    BACKEND = 'getpaid.backends.dotpay'
    BACKEND_NAME = _('Dotpay')
    BACKEND_ACCEPTED_CURRENCY = ('PLN', 'EUR', 'USD', 'GBP', 'JPY', 'CZK', 'SEK')
    BACKEND_LOGO_URL = 'getpaid/backends/dotpay/dotpay_logo.png'

    _ALLOWED_IP = ('195.150.9.37', )
    _ACCEPTED_LANGS = ('pl', 'en', 'de', 'it', 'fr', 'es', 'cz', 'ru', 'bg')
    _GATEWAY_URL = 'https://ssl.dotpay.pl/t2/'
    _ONLINE_SIG_FIELDS = (
        'id', 'operation_number', 'operation_type', 'operation_status',
        'operation_amount', 'operation_currency', 'operation_withdrawal_amount',
        'operation_commission_amount', 'is_completed', 'operation_original_amount',
        'operation_original_currency', 'operation_datetime', 'operation_related_number', 'control',
        'description', 'email', 'p_info', 'p_email', 'credit_card_issuer_identification_number',
        'credit_card_masked_number', 'credit_card_brand_codename', 'credit_card_brand_code',
        'credit_card_id', 'channel', 'channel_country', 'geoip_country'
    )

    @staticmethod
    def compute_sig(params, fields, PIN):
        text = PIN + ''.join(map(lambda field: params.get(field, ''), fields))
        return hashlib.sha256(text.encode('utf8')).hexdigest()

    @staticmethod
    def online(params, ip, settings_object):
        PIN = settings_object.get_configuration_value('PIN', '')

        if params['signature'] != PaymentProcessor.compute_sig(params, PaymentProcessor._ONLINE_SIG_FIELDS, PIN):
            print('Got message with wrong sig, %s' % str(params))
            logger.warning('Got message with wrong sig, %s' % str(params))
            return u'SIG ERR'

        try:
            params['id'] = int(params['id'])
        except ValueError:
            return u'ID ERR'
        if params['id'] != int(settings_object.get_configuration_value('id')):
            return u'ID ERR'

        from getpaid.models import Payment
        try:
            payment = Payment.objects.get(pk=int(params['control']))
        except (ValueError, Payment.DoesNotExist):
            logger.error('Got message for non existing Payment, %s' % str(params))
            return u'PAYMENT ERR'

        amount = params.get('operation_original_amount', params['operation_amount'])
        currency = params.get('operation_original_currency', params['operation_currency'])

        if currency != payment.currency.upper():
            logger.error('Got message with wrong currency, %s' % str(params))
            return u'CURRENCY ERR'

        payment.external_id = params.get('operation_number', '')
        payment.description = params.get('email', '')

        if params['operation_status'] == DotpayTransactionStatus.FINISHED:
            payment.amount_paid = Decimal(amount)
            payment.paid_on = datetime.datetime.utcnow().replace(tzinfo=utc)
            if payment.amount <= Decimal(amount):
                # Amount is correct or it is overpaid
                payment.change_status('paid')
            else:
                payment.change_status('partially_paid')
        elif params['operation_status'] == DotpayTransactionStatus.REJECTED:
            payment.change_status('failed')

        return u'OK'

    def get_URLC(self, settings_object):
        urlc = reverse('getpaid-dotpay-online')
        if PaymentProcessor.get_backend_setting('force_ssl', True):
            return u'https://%s%s' % (settings_object.get_domain(), urlc)
        else:
            return u'http://%s%s' % (settings_object.get_domain(), urlc)

    def get_URL(self, settings_object, pk):
        url = reverse('getpaid-dotpay-return', kwargs={'pk': pk})
        if PaymentProcessor.get_backend_setting('force_ssl', True):
            return u'https://%s%s' % (settings_object.get_domain(), url)
        else:
            return u'http://%s%s' % (settings_object.get_domain(), url)

    def get_gateway_url(self, request, settings_object):
        """
        Routes a payment to Gateway, should return URL for redirection.
        """
        params = {
            'id': settings_object.get_configuration_value('id'),
            'description': self.get_order_description(self.payment, self.payment.order),
            'amount': self.payment.amount,
            'currency': self.payment.currency,
            'type': 0,  # show "return" button after finished payment
            'control': self.payment.pk,
            'URL': self.get_URL(pk=self.payment.pk, settings_object=settings_object),
            'URLC': self.get_URLC(settings_object=settings_object),
        }

        user_data = {
            'email': None,
            'lang': None,
        }
        signals.user_data_query.send(sender=None, order=self.payment.order, user_data=user_data)

        if user_data['email']:
            params['email'] = user_data['email']

        if user_data['lang'] and user_data['lang'].lower() in PaymentProcessor._ACCEPTED_LANGS:
            params['lang'] = user_data['lang'].lower()
        elif PaymentProcessor.get_backend_setting('lang', False) and \
                        PaymentProcessor.get_backend_setting('lang').lower() in PaymentProcessor._ACCEPTED_LANGS:
            params['lang'] = PaymentProcessor.get_backend_setting('lang').lower()

        if PaymentProcessor.get_backend_setting('onlinetransfer', False):
            params['onlinetransfer'] = 1
        if PaymentProcessor.get_backend_setting('p_email', False):
            params['p_email'] = PaymentProcessor.get_backend_setting('p_email')
        if PaymentProcessor.get_backend_setting('p_info', False):
            params['p_info'] = PaymentProcessor.get_backend_setting('p_info')
        if PaymentProcessor.get_backend_setting('tax', False):
            params['tax'] = 1

        gateway_url = PaymentProcessor.get_backend_setting('gateway_url', self._GATEWAY_URL)

        if PaymentProcessor.get_backend_setting('method', 'get').lower() == 'post':
            return gateway_url, 'POST', params
        elif PaymentProcessor.get_backend_setting('method', 'get').lower() == 'get':
            for key in params.keys():
                params[key] = six.text_type(params[key]).encode('utf-8')
            return gateway_url + '?' + urlencode(params), "GET", {}
        else:
            raise ImproperlyConfigured('Dotpay payment backend accepts only GET or POST')
