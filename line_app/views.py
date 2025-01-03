from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from django.contrib.auth.models import User
from attendance_app.models import LeaveAttendance
from line_app.models import UserProfile
from linebot.models import (
    MessageEvent, FollowEvent, PostbackEvent, TextMessage,
    PostbackAction, TemplateSendMessage, ButtonsTemplate, TextSendMessage
)
from django.shortcuts import render
import json

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)


def register(request):
    return render(request, 'line_app/register.html')


@handler.add(FollowEvent)
def handle_follow(event):
    try:
        line_id = event.source.user_id
        profile = line_bot_api.get_profile(line_id)

        # Check if the profile exists
        profile_exists = UserProfile.objects.filter(line_id=line_id).exists()
        if profile_exists:
            user_profile = UserProfile.objects.get(line_id=line_id)
            user_profile.line_name = profile.display_name
            user_profile.line_picture_url = profile.picture_url
            user_profile.line_status_message = profile.status_message
            user_profile.unfollow = False
            user_profile.save()
        else:
            UserProfile.objects.create(
                line_id=line_id,
                line_name=profile.display_name,
                line_picture_url=profile.picture_url,
                line_status_message=profile.status_message,
            )
    except Exception as e:
        print(f"Error in handle_follow: {e}")


@handler.add(PostbackEvent)
def handle_postback(event):
    try:
        data = event.postback.data  # Get postback data
        line_id = event.source.user_id  # Get the Line ID of the approver

        # Parse the postback data
        postback_data = dict(item.split('=') for item in data.split('&'))
        action = postback_data.get('action')
        leave_id = postback_data.get('leave_id')

        if not leave_id:
            print("ไม่พบรหัสคำขอการลา !")
            return

        # Retrieve the LeaveAttendance record
        leave_record = LeaveAttendance.objects.filter(id=leave_id).first()
        if not leave_record:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ไม่พบรหัสคำขอการลา !")
            )
            return

        # Check if already approved or rejected
        if leave_record.status in ["approved", "rejected"]:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ไม่สามารถทำซ้ำได้ มีการพิจารณาคำขอการลานี้ไปแล้ว !")
            )
            return

        # Process the approval or rejection
        if action == "approve":
            leave_record.status = "approved"
            response_message = "อนุมัติคำขอการลาเสร็จสิ้น !"
        elif action == "reject":
            leave_record.status = "rejected"
            response_message = "ปฏิเสธคำขอการลาเสร็จสิ้น !"
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="Unknown action.")
            )
            return

        leave_record.save()

        # Send confirmation message to approver
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_message)
        )

        # Optionally notify the requester
        requester_line_id = leave_record.user.uid
        if requester_line_id:
            line_bot_api.push_message(
                requester_line_id,
                TextSendMessage(text=f"คำขอการลาของคุณได้รับการ {leave_record.status} !")
            )
    except Exception as e:
        print(f"Error in handle_postback: {e}")


@csrf_exempt
def callback(request):
    if request.method == "POST":
        # Get X-Line-Signature header value
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            return HttpResponseBadRequest()
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
