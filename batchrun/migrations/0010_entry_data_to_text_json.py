# Generated by Django 2.2.13 on 2021-08-16 09:47

import batchrun.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("batchrun", "0009_jobhistoryretentionpolicy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobrunlog",
            name="entry_data",
            field=batchrun.fields.TextJSONField(
                blank=True,
                help_text=(
                    "Data that defines the location, timestamp and "
                    "kind (stdout or stderr) of each log entry within "
                    "the whole log content."
                ),
                null=True,
                verbose_name="log entry metadata",
            ),
        ),
    ]
