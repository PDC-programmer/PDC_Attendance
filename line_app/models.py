from django.db import models


# Create your models here.
class UserProfile(models.Model):
    # get from line
    id = models.AutoField(primary_key=True)
    line_id = models.CharField(max_length=100, verbose_name="LineID")
    line_name = models.CharField(max_length=100, verbose_name="LineName")
    line_picture_url = models.URLField(verbose_name="LinePictureURL")
    line_status_message = models.CharField(max_length=100, blank=True, null=True, verbose_name="LineStatus")
    # generated by system
    unfollow = models.BooleanField(default=False, verbose_name="Unfollow")
    create_time = models.DateTimeField(auto_now=True, verbose_name="CreateTime")