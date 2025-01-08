# Generated by Django 5.1.4 on 2025-01-08 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('line_id', models.CharField(max_length=100, verbose_name='LineID')),
                ('line_name', models.CharField(max_length=100, verbose_name='LineName')),
                ('line_picture_url', models.URLField(verbose_name='LinePictureURL')),
                ('line_status_message', models.CharField(blank=True, max_length=100, null=True, verbose_name='LineStatus')),
                ('unfollow', models.BooleanField(default=False, verbose_name='Unfollow')),
                ('create_time', models.DateTimeField(auto_now=True, verbose_name='CreateTime')),
            ],
        ),
    ]
