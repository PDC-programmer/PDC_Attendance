# Generated by Django 5.1.4 on 2025-02-05 14:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_app', '0002_alter_bsnstaff_brc_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='nick_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
