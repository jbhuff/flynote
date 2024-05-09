# Generated by Django 3.1.4 on 2023-11-27 00:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flynote', '0011_airfield_airfield_to_uta'),
    ]

    operations = [
        migrations.CreateModel(
            name='wandb_item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=40)),
                ('weight', models.IntegerField(null=True)),
                ('arm', models.IntegerField()),
                ('aircraft', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flynote.aircraft')),
            ],
        ),
    ]
