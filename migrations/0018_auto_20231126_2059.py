# Generated by Django 3.1.4 on 2023-11-27 01:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flynote', '0017_auto_20231126_2055'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ac_item',
            old_name='name',
            new_name='category',
        ),
    ]
