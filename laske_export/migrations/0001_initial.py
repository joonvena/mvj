# Generated by Django 2.1.3 on 2018-11-15 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('leasing', '0031_vat'),
    ]

    operations = [
        migrations.CreateModel(
            name='LaskeExportLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.DateTimeField(editable=False, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Time created')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Time modified')),
                ('started_at', models.DateTimeField(verbose_name='Time started')),
                ('ended_at', models.DateTimeField(blank=True, null=True, verbose_name='Time ended')),
                ('is_finished', models.BooleanField(default=False, verbose_name='Finished?')),
                ('invoices', models.ManyToManyField(to='leasing.Invoice')),
            ],
            options={
                'verbose_name': 'Laske export log',
                'verbose_name_plural': 'Laske export logs',
                'ordering': ['-created_at'],
            },
        ),
    ]