# Generated by Django 3.1.4 on 2023-11-25 16:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flynote', '0007_maintlogitem_logitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintlogitem',
            name='oil_changed',
            field=models.BooleanField(default=False),
        ),
    ]
