import pymysql
import os
from django.core.management.base import BaseCommand
from linebot import LineBotApi
from linebot.models import TemplateSendMessage, ButtonsTemplate, PostbackAction, MessageAction, URIAction
from datetime import datetime, timedelta
from approval_app.models import Approval
from allauth.socialaccount.models import SocialAccount
from user_app.models import User


class Command(BaseCommand):
    help = "remind approve user to complete the requestions"

    def handle(self, *args, **kwargs):

        # ตั้งค่า LINE API
        line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

        requestions = Approval.objects.filter(status="pending", approve_user__isnull=False)
        approve_staff_ids = requestions.values_list("approve_user", flat=True).distinct()
        approve_staff = User.objects.filter(id__in=approve_staff_ids)

        for user in approve_staff:
            social_account = SocialAccount.objects.filter(user=user).first()
            line_id = social_account.uid

            # สร้างข้อความ Template Message
            message = TemplateSendMessage(
                alt_text="แจ้งเตือนรายการที่ต้องพิจารณา ก่อน 16:00 น.",
                template=ButtonsTemplate(
                    title="แจ้งเตือนรายการที่ต้องพิจารณา ก่อน 16:00 น.",
                    text=f"เรียนคุณ {user.get_full_name()}\nคุณมีรายการที่ต้องพิจารณาหลือ {requestions.filter(approve_user=user).count()} รายการ\n",
                    actions=[
                        URIAction(label=f"{requestions.filter(approve_user=user).count()} รายการที่ต้องพิจารณา",
                                  uri=f"https://plusdentalclinic-attendance-ec6ce5056c43.herokuapp.com/approval/approval-list/?search=&approval_type=&status=pending")
                    ]
                )
            )

            # ส่งข้อความไปยัง LINE
            try:
                line_bot_api.push_message(line_id, message)
                self.stdout.write(self.style.SUCCESS(f"✅ แจ้งเตือนไปที่ {user.get_full_name()} (รหัสพนักงาน: {user.username})"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ แจ้งเตือนไปที่ {user.get_full_name()} (รหัสพนักงาน: {user.username}) ล้มเหลว: {e}"))
