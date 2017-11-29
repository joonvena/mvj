# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-28 11:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leasing', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Time created')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Time modified')),
                ('type', models.PositiveSmallIntegerField(choices=[(1, 'Plot'), (2, 'Real estate'), (3, 'Allotment garden parcel')], null=True, verbose_name='Type')),
                ('address', models.CharField(max_length=255, verbose_name='Address')),
                ('surface_area', models.PositiveIntegerField(blank=True, null=True, verbose_name='Surface area in square meters')),
                ('leases', models.ManyToManyField(blank=True, related_name='assets', to='leasing.Lease', verbose_name='Leases')),
            ],
            options={
                'verbose_name_plural': 'Assets',
                'verbose_name': 'Asset',
            },
        ),
    ]
