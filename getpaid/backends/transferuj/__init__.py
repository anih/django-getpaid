from decimal import Decimal
import hashlib
import logging

from django import forms
from six.moves.urllib.parse import urlencode
import datetime
from django.utils.six import text_type
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.apps import apps
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from getpaid import signals
from getpaid.backends import PaymentProcessorBase

logger = logging.getLogger('getpaid.backends.transferuj')


class PaymentProcessor(PaymentProcessorBase):
    configuration_options = {
        'id': forms.IntegerField(label='Transferuj - ID sprzedawcy'),
        'key': forms.CharField(label='Transferuj - Klucz sprzedawcy'),
    }

    BACKEND = u'getpaid.backends.transferuj'
    BACKEND_NAME = _(u'Transferuj.pl')
    BACKEND_ACCEPTED_CURRENCY = (u'PLN', )
    BACKEND_LOGO_URL = u'getpaid/backends/transferuj/transferuj_logo.png'

    _GATEWAY_URL = u'https://secure.transferuj.pl'
    _REQUEST_SIG_FIELDS = (u'id', u'kwota', u'crc',)
    _ALLOWED_IP = (u'195.149.229.109', )

    _ONLINE_SIG_FIELDS = (u'id', u'tr_id', u'tr_amount', u'tr_crc', )
    _ACCEPTED_LANGS = (u'pl', u'en', u'de')

    @staticmethod
    def compute_sig(params, fields, key):
        text = u''
        for field in fields:
            text += text_type(params.get(field, ''))
        text += key
        text_encoded = text.encode('utf-8')
        return text_type(hashlib.md5(text_encoded).hexdigest())

    @staticmethod
    def online(
            ip, id, tr_id, tr_date, tr_crc, tr_amount,
            tr_paid, tr_desc, tr_status, tr_error, tr_email, md5sum,
            settings_object
    ):

        allowed_ip = PaymentProcessor.get_backend_setting('allowed_ip',
            PaymentProcessor._ALLOWED_IP)

        if len(allowed_ip) != 0 and ip not in allowed_ip:
            logger.warning('Got message from not allowed IP %s' % str(allowed_ip))
            return u'IP ERR'

        params = {'id': id, 'tr_id': tr_id, 'tr_amount': tr_amount, 'tr_crc': tr_crc}
        key = settings_object.get_configuration_value('key')

        if md5sum != PaymentProcessor.compute_sig(params, PaymentProcessor._ONLINE_SIG_FIELDS, key):
            logger.warning('Got message with wrong sig, %s' % str(params))
            return u'SIG ERR'

        if int(id) != int(settings_object.get_configuration_value('id')):
            logger.warning('Got message with wrong id, %s' % str(params))
            return u'ID ERR'

        Payment = apps.get_model('getpaid', 'Payment')
        try:
            payment = Payment.objects.select_related('order').get(pk=int(tr_crc))
        except (Payment.DoesNotExist, ValueError):
            logger.error('Got message with CRC set to non existing Payment, %s' % str(params))
            return u'CRC ERR'

        logger.info('Incoming payment: id=%s, tr_id=%s, tr_date=%s, tr_crc=%s, tr_amount=%s, tr_paid=%s, tr_desc=%s, tr_status=%s, tr_error=%s, tr_email=%s' % (id, tr_id, tr_date, tr_crc, tr_amount, tr_paid, tr_desc, tr_status, tr_error, tr_email))

        payment.external_id = tr_id
        payment.description = tr_email

        if tr_status == u'TRUE':
            # Due to Transferuj documentation, we need to check if amount is correct
            payment.amount_paid = Decimal(tr_paid)
            payment.paid_on = datetime.datetime.utcnow().replace(tzinfo=utc)
            if payment.amount <= Decimal(tr_paid):
                # Amount is correct or it is overpaid
                payment.change_status('paid')
            else:
                payment.change_status('partially_paid')
        elif payment.status != 'paid':
            payment.change_status('failed')

        return u'TRUE'

    def get_gateway_url(self, request, settings_object):
        "Routes a payment to Gateway, should return URL for redirection."
        params = {
            'id': settings_object.get_configuration_value('id'),
            'opis': self.get_order_description(self.payment,
                                               self.payment.order),
            # Here we put payment.pk as we can get order through payment model
            'crc': self.payment.pk,
            # amount is  in format XXX.YY PLN
            'kwota': text_type(self.payment.amount),
        }

        self._build_user_data(params, settings_object=settings_object)
        self._build_md5sum(params, settings_object=settings_object)
        self._build_urls(params, settings_object=settings_object)

        method = PaymentProcessor.get_backend_setting('method', 'get').lower()
        if method not in ('post', 'get'):
            raise ImproperlyConfigured(
                'Transferuj.pl payment backend accepts only GET or POST'
            )

        if method == 'post':
            return self._GATEWAY_URL, 'POST', params

        params = {k: text_type(v).encode('utf-8') for k, v in params.items()}
        return "{}?{}".format(self._GATEWAY_URL, urlencode(params)), "GET", {}

    def _build_user_data(self, params, settings_object):
        user_data = {
            'email': None,
            'lang': None,
        }
        signals.user_data_query.send(sender=None,
                                     order=self.payment.order,
                                     user_data=user_data)

        for lang in (user_data['lang'], PaymentProcessor.get_backend_setting('lang', '')):
            if lang and lang.lower() in self._ACCEPTED_LANGS:
                params['jezyk'] = lang.lower()
                break
        if user_data['email']:
            params['email'] = user_data['email']

        return params

    def _build_md5sum(self, params, settings_object):
        if not PaymentProcessor.get_backend_setting('signing', True):
            return params

        params['md5sum'] = self.compute_sig(
            params, self._REQUEST_SIG_FIELDS,
            settings_object.get_configuration_value('key'))

        return params

    def _build_urls(self, params, settings_object):
        domain = settings_object.get_domain()
        online_domain = return_domain = "http"

        if PaymentProcessor.get_backend_setting('force_ssl_online', True):
            online_domain = "https"
        if PaymentProcessor.get_backend_setting('force_ssl_return', True):
            return_domain = "https"

        online_domain = "{}://{}".format(online_domain, domain)
        return_domain = "{}://{}".format(return_domain, domain)

        params['wyn_url'] = online_domain + reverse(
            'getpaid-transferuj-online'
        )
        params['pow_url'] = return_domain + reverse(
            'getpaid-transferuj-success', kwargs={'pk': self.payment.pk}
        )
        params['pow_url_blad'] = return_domain + reverse(
            'getpaid-transferuj-failure', kwargs={'pk': self.payment.pk}
        )

        return params
