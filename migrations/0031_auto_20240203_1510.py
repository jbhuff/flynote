# Generated by Django 3.1.4 on 2024-02-03 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flynote', '0030_auto_20240203_1500'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='airfield_to_uta',
            name='field_elevation',
        ),
        migrations.RemoveField(
            model_name='airfield_to_uta',
            name='pattern_altitude',
        ),
        migrations.AddField(
            model_name='airfield',
            name='field_elevation',
            field=models.IntegerField(default=999),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='airfield',
            name='pattern_altitude',
            field=models.IntegerField(default=9999),
            preserve_default=False,
        ),
    ]
