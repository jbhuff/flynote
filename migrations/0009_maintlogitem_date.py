# Generated by Django 3.1.4 on 2023-11-25 16:28

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('flynote', '0008_maintlogitem_oil_changed'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintlogitem',
            name='date',
            field=models.DateField(default=datetime.datetime(2023, 11, 25, 16, 28, 24, 672535, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
