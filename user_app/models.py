from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from branch_app.models import BsnBranch
import os


def user_image_path(instance, filename):
    return os.path.join(f"user_images/{instance.username}", filename)


class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    image = models.ImageField(upload_to=user_image_path, null=True, blank=True)
    role = models.CharField(max_length=100, null=True, blank=True)
    nick_name = models.CharField(max_length=100, null=True, blank=True)


class BsnStaff(models.Model):
    staff_id = models.BigIntegerField(blank=True, null=True)
    staff_code = models.CharField(max_length=128, blank=True, null=True)
    staff_pin = models.CharField(max_length=13, blank=True, null=True)
    staff_pname = models.CharField(max_length=100, blank=True, null=True)
    staff_fname = models.CharField(max_length=255, blank=True, null=True)
    staff_lname = models.CharField(max_length=255, blank=True, null=True)
    staff_fname_en = models.CharField(max_length=255, blank=True, null=True)
    staff_lname_en = models.CharField(max_length=255, blank=True, null=True)
    staff_department = models.CharField(max_length=255, blank=True, null=True)
    staff_title = models.CharField(max_length=255, blank=True, null=True)
    usr_name = models.CharField(max_length=255, blank=True, null=True)
    usr_passwd = models.CharField(max_length=128, blank=True, null=True)
    brc_id = models.ForeignKey(BsnBranch,
                               on_delete=models.DO_NOTHING,
                               related_name="fk_bsnbranch",
                               blank=True,
                               null=True)
    brc_chkin_status = models.CharField(max_length=254, blank=True, null=True)
    mng_staff_id = models.BigIntegerField(blank=True, null=True)
    date_of_start = models.DateField(blank=True, null=True)
    date_of_resign = models.DateField(blank=True, null=True)
    staff_type = models.CharField(max_length=100, blank=True, null=True)
    staff_regis_status = models.CharField(max_length=100, blank=True, null=True)
    staff_req_status = models.CharField(max_length=100, blank=True, null=True)
    device_no = models.CharField(max_length=128, blank=True, null=True)
    insert_usr_id = models.BigIntegerField(blank=True, null=True)
    date_of_insert = models.DateTimeField(blank=True, null=True)
    update_usr_id = models.BigIntegerField(blank=True, null=True)
    date_of_update = models.DateTimeField(blank=True, null=True)
    delete_usr_id = models.BigIntegerField(blank=True, null=True)
    date_of_delete = models.DateTimeField(blank=True, null=True)
    django_usr_id = models.ForeignKey(User,
                                      on_delete=models.DO_NOTHING,
                                      related_name="django_usr_id",
                                      blank=True,
                                      null=True
                                      )
    group = models.ForeignKey(Group,
                              on_delete=models.DO_NOTHING,
                              related_name="group",
                              blank=True,
                              null=True,
                              )

    class Meta:
        db_table = 'bsn_staff'
