# -*- coding:utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from django.apps import AppConfig


class GetPaidPaypalAppConfig(AppConfig):
    name = 'getpaid.backends.paypal'
    label = 'getpaid_paypal'
    verbose_name = "GetPaid PayPal backend"
