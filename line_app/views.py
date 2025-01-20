from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from django.contrib.auth.models import User
from attendance_app.models import LeaveAttendance, LeaveBalance, LeaveBalanceInitial
from line_app.models import UserProfile
from user_app.models import User, BsnStaff
from linebot.models import (
    MessageEvent, FollowEvent, PostbackEvent, TextMessage,
    PostbackAction, TemplateSendMessage, ButtonsTemplate, TextSendMessage
)
from django.shortcuts import render, get_object_or_404
import json
from django.http import JsonResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

# Mapping for leave type display names
STATUS_DISPLAY = {
    'approved': 'อนุมัติ',
    'rejected': 'ปฏิเสธ',
}


@login_required(login_url='log-in')
@csrf_exempt
def register_line_id(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            staff_code = data.get("staffCode")

            # ค้นหา BsnStaff จาก staff_code
            get_staff_name = BsnStaff.objects.filter(staff_code=staff_code).first()
            if not get_staff_name:
                return JsonResponse({"error": "ไม่พบข้อมูลพนักงาน !"}, status=404)

            # ตรวจสอบว่าผู้ใช้งานเคยลงทะเบียนแล้วหรือยัง
            if get_staff_name.django_usr_id:
                if get_staff_name.django_usr_id == request.user:
                    return JsonResponse({"error": "บัญชีของคุณได้ทำการลงทะเบียนไปแล้ว."}, status=400)
                else:
                    return JsonResponse({"error": "รหัสพนักงานถูกใช้ลงทะเบียนไปแล้ว !"},
                                        status=400)

            # อัปเดตข้อมูล User
            user = request.user
            user.first_name = get_staff_name.staff_fname
            user.last_name = get_staff_name.staff_lname
            user.username = get_staff_name.staff_code
            user.role = get_staff_name.staff_type
            user.save()

            # ค้นหา LeaveBalanceInitial ตาม staff_code
            leave_balances_initial = LeaveBalanceInitial.objects.filter(staff_code=staff_code)
            if not leave_balances_initial.exists():
                return JsonResponse({"error": "No leave balance found for staff"}, status=404)

            # บันทึกข้อมูลใน LeaveBalance
            for initial_balance in leave_balances_initial:
                LeaveBalance.objects.update_or_create(
                    user=user,
                    leave_type=initial_balance.leave_type,
                    defaults={
                        "total_hours": initial_balance.total_hours,
                        "remaining_hours": initial_balance.remaining_hours,
                    }
                )

            # อัปเดต django_usr_id ของ BsnStaff
            staff = BsnStaff.objects.get(staff_code=staff_code)
            staff.django_usr_id = user
            staff.save()

            return JsonResponse({"success": True, "message": "Registration successful."}, status=200)

        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    return render(request, 'line_app/register_line_id.html')


@csrf_exempt
def register(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_id = data.get("userID")
        staff_code = data.get("staffCode")

        # ค้นหาผู้อนุมัติจากตาราง BsnStaff
        staff = BsnStaff.objects.filter(staff_code=staff_code).first()
        if not staff:
            return JsonResponse({"error": "Staff not found"}, status=404)

        django_usr_id = User.objects.filter(id=staff.django_usr_id.id).first()
        if not django_usr_id:
            return JsonResponse({"error": "User not found"}, status=404)
        else:
            user = User.objects.get(id=django_usr_id.id)
            user.uid = user_id
            user.save()
            return JsonResponse({"success": True, "message": "Registration successful."}, status=200)

    return render(request, 'line_app/register.html')


def get_staff_info(request, staff_code):
    staff = BsnStaff.objects.filter(staff_code=staff_code).first()
    if not staff:
        return JsonResponse({"error": "ไม่พบข้อมูลพนักงาน"}, status=404)
    return JsonResponse({
        "staff_code": staff.staff_code,
        "staff_fname": staff.staff_fname,
        "staff_lname": staff.staff_lname,
        "staff_title": staff.staff_title,
        "staff_department": staff.staff_department,
    }, status=200)


@login_required
def user_info(request):
    users = request.user
    social_account = SocialAccount.objects.filter(user=users)
    template = loader.get_template('line_app/user_info.html')
    context = {
        'users': social_account,
    }
    return HttpResponse(template.render(context, request))


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
        line_id = event.source.user_id  # Get the Line ID of the approver or requester

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
        if leave_record.status in ["cancelled"]:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="ไม่สามารถทำรายการได้ คำขออนุมัตินี้ยกเลิกไปแล้ว !")
            )
        elif leave_record.status in ["approved", "rejected"] and action in ["approve", "reject"]:
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
        elif action == "cancel":
            leave_record.status = "cancelled"
            response_message = "ยกเลิกคำขอการลาเสร็จสิ้น !"
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="Unknown action.")
            )
            return

        leave_record.save()

        status_display = STATUS_DISPLAY.get(leave_record.status, "Unknown Status")

        # Send confirmation message to approver
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_message)
        )

        # Optionally notify the requester
        social_account = SocialAccount.objects.filter(user=leave_record.user, provider="line").first()
        requester_line_id = social_account.uid if social_account else None
        if requester_line_id and action in ["approve", "reject"]:
            line_bot_api.push_message(
                requester_line_id,
                TextSendMessage(text=f"คำขอการลาของคุณได้รับการ {leave_record.get_status_display()} !")
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
