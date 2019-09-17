# Generated by Django 2.2.5 on 2019-09-16 12:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leasing', '0072_tenantrentshare'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicerow',
            name='intended_use',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='leasing.RentIntendedUse', verbose_name='Intended use'),
        ),
    ]
