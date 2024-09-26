# Generated by Django 4.2.6 on 2024-09-22 09:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("vehicle", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="vehicle_user",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
