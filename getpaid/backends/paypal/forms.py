#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django import forms
from getpaid.backends.paypal.models import PaymentPaypal

# 20:18:05 Jan 30, 2009 PST - PST timezone support is not included out of the box.
# PAYPAL_DATE_FORMAT = ("%H:%M:%S %b. %d, %Y PST", "%H:%M:%S %b %d, %Y PST",)
# PayPal dates have been spotted in the wild with these formats, beware!
PAYPAL_DATE_FORMAT = ("%H:%M:%S %d %b %Y PST",
                      "%H:%M:%S %b. %d, %Y PST",
                      "%H:%M:%S %b. %d, %Y PDT",
                      "%H:%M:%S %b %d, %Y PST",
                      "%H:%M:%S %b %d, %Y PDT",)

class PayPalStandardBaseForm(forms.ModelForm):
    """Form used to receive and record PayPal IPN/PDT."""
    # PayPal dates have non-standard formats.
    time_created = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
    payment_date = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
    next_payment_date = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
    subscr_date = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)
    subscr_effective = forms.DateTimeField(required=False, input_formats=PAYPAL_DATE_FORMAT)

    def get_global_errors(self):
        errors = dict(self.errors)
        return list(errors.get("__all__", []))

class PayPalIPNForm(PayPalStandardBaseForm):
    """
    Form used to receive and record PayPal IPN notifications.
    
    PayPal IPN test tool:
    https://developer.paypal.com/us/cgi-bin/devscr?cmd=_tools-session
    """
    class Meta:
        model = PaymentPaypal

