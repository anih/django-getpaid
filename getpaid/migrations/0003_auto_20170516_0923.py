# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('getpaid', '0002_auto_20150723_0923'),
        migrations.swappable_dependency(settings.GETPAID_PAYMENT_CONFIGURATION),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payment_configuration',
            field=models.ForeignKey(related_name='payments', to=settings.GETPAID_PAYMENT_CONFIGURATION),
        ),
    ]
