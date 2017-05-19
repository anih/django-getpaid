# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import swapper
from django.db import migrations


def fill_payment_configutarions(apps, schema_editor):
    Payment = apps.get_model("getpaid", "Payment")
    PaymentConfiguration = apps.get_model(swapper.get_model_name("getpaid", "PaymentConfiguration"))
    for payment in Payment.objects.all():
        configuration, _ = PaymentConfiguration.objects.get_or_create(backend=payment.backend)
        payment.payment_configuration = configuration
        payment.save()


class Migration(migrations.Migration):
    dependencies = [
        ('getpaid', '0003_auto_20170516_0923'),
    ]

    operations = [
        migrations.RunPython(fill_payment_configutarions),
    ]
