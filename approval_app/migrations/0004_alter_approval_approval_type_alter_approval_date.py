# Generated by Django 5.1.4 on 2025-03-05 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('approval_app', '0003_approval_shift_day'),
    ]

    operations = [
        migrations.AlterField(
            model_name='approval',
            name='approval_type',
            field=models.CharField(blank=True, choices=[('leave', 'ขอลา'), ('shift', 'เปลี่ยนกะทำงาน')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='approval',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
