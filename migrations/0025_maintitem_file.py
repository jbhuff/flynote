# Generated by Django 3.1.4 on 2023-12-29 00:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flynote', '0024_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='Maintitem_file',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flynote.file')),
                ('maintitem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='flynote.maintlogitem')),
            ],
        ),
    ]
