# Generated by Django 3.1.4 on 2024-02-03 21:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('flynote', '0031_auto_20240203_1510'),
    ]

    operations = [
        migrations.CreateModel(
            name='Minimums',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visibility', models.IntegerField(default=5)),
                ('ceiling', models.IntegerField(default=3000)),
                ('wind', models.IntegerField(default=16)),
                ('crosswind', models.IntegerField(default=8)),
                ('takeoff_mult', models.IntegerField(default=2)),
                ('landing_mult', models.IntegerField(default=2)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
