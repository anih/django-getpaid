# -*- coding:utf-8 -*-
from importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from getpaid.backends import PaymentProcessorBase


class PaymentProcessor(PaymentProcessorBase):
    BACKEND = 'getpaid.backends.regular_transfer'
    BACKEND_NAME = _(u'Regular transfer')
    BACKEND_ACCEPTED_CURRENCY = ('PLN', 'EUR', 'USD')

    def get_gateway_url(self, request, settings_object):
        """
        Routes a payment to view from configurations.
        """

        module_name = PaymentProcessor.get_backend_setting('module_name')
        module = import_module(module_name)
        url = module.get_regular_transfer_url(self.payment)
        if not isinstance(url, basestring):
            raise ImproperlyConfigured('Regular transfer backend have wrong url class in config')
        return url, 'GET', {}
