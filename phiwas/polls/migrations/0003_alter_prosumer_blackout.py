# Generated by Django 4.1.dev20211123065844 on 2022-01-10 18:31

import django.contrib.auth.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0002_prosumer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prosumer',
            name='blackout',
            field=models.BooleanField(verbose_name=django.contrib.auth.models.User),
        ),
    ]
