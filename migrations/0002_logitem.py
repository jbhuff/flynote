# Generated by Django 3.1.4 on 2023-11-24 01:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flynote', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Logitem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('logtype', models.CharField(max_length=50)),
                ('note', models.CharField(max_length=2000)),
                ('uta', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='flynote.user_to_aircraft')),
            ],
        ),
    ]
