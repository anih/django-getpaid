# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django
import swapper
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('getpaid', '0002_auto_20150723_0923'),
        swapper.dependency('getpaid', 'PaymentConfiguration'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentConfiguration',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('backend', models.CharField(max_length=50)),
                ('configuration', models.TextField()),
            ],
            options={
                'swappable': swapper.swappable_setting('getpaid', 'PaymentConfiguration'),
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_configuration',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=swapper.get_model_name('getpaid', 'PaymentConfiguration'),
                null=True
            ),
        ),
    ]
