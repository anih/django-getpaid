# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('getpaid', '0004_payment_configuration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='payment_configuration',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=swapper.get_model_name('getpaid', 'PaymentConfiguration')
            ),
            preserve_default=False,
        ),
    ]
