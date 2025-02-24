from django.db import models


# Create your models here.
class BsnBranch(models.Model):
    brc_id = models.BigIntegerField(blank=True, null=True)
    bsn_id = models.BigIntegerField(blank=True, null=True)
    brc_logo = models.CharField(max_length=254, blank=True, null=True)
    brc_code = models.CharField(max_length=255, blank=True, null=True)
    brc_name = models.CharField(max_length=254, blank=True, null=True)
    brc_name_en = models.CharField(max_length=254, blank=True, null=True)
    brc_sname = models.CharField(max_length=254, blank=True, null=True)
    brc_addr_line1 = models.CharField(max_length=254, blank=True, null=True)
    brc_addr_line2 = models.CharField(max_length=254, blank=True, null=True)
    brc_addr_prov = models.CharField(max_length=255, blank=True, null=True)
    brc_addr_city = models.CharField(max_length=255, blank=True, null=True)
    brc_addr_suburb = models.CharField(max_length=255, blank=True, null=True)
    brc_addr_zipcode = models.CharField(max_length=255, blank=True, null=True)
    brc_tel_no = models.CharField(max_length=254, blank=True, null=True)
    brc_email_addr = models.CharField(max_length=254, blank=True, null=True)
    gps_lat = models.CharField(max_length=254, blank=True, null=True)
    gps_lng = models.CharField(max_length=254, blank=True, null=True)
    slot_min_time = models.TimeField(blank=True, null=True)
    slot_max_time = models.TimeField(blank=True, null=True)
    slot_duration = models.TimeField(blank=True, null=True)

    class Meta:
        db_table = 'bsn_branch'
