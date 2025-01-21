# Generated by Django 5.1.4 on 2025-01-21 13:32

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BsnBranch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('brc_id', models.BigIntegerField(blank=True, null=True)),
                ('bsn_id', models.BigIntegerField(blank=True, null=True)),
                ('brc_logo', models.CharField(blank=True, max_length=254, null=True)),
                ('brc_code', models.CharField(blank=True, max_length=255, null=True)),
                ('brc_name', models.CharField(blank=True, max_length=254, null=True)),
                ('brc_name_en', models.CharField(blank=True, max_length=254, null=True)),
                ('brc_sname', models.CharField(blank=True, max_length=254, null=True)),
                ('brc_addr_line1', models.CharField(blank=True, max_length=254, null=True)),
                ('brc_addr_line2', models.CharField(blank=True, max_length=254, null=True)),
                ('brc_addr_prov', models.CharField(blank=True, max_length=255, null=True)),
                ('brc_addr_city', models.CharField(blank=True, max_length=255, null=True)),
                ('brc_addr_suburb', models.CharField(blank=True, max_length=255, null=True)),
                ('brc_addr_zipcode', models.CharField(blank=True, max_length=255, null=True)),
                ('brc_tel_no', models.CharField(blank=True, max_length=254, null=True)),
                ('brc_email_addr', models.CharField(blank=True, max_length=254, null=True)),
                ('gps_lat', models.CharField(blank=True, max_length=254, null=True)),
                ('gps_lng', models.CharField(blank=True, max_length=254, null=True)),
                ('slot_min_time', models.TimeField(blank=True, null=True)),
                ('slot_max_time', models.TimeField(blank=True, null=True)),
                ('slot_duration', models.TimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'bsn_branch',
            },
        ),
    ]
