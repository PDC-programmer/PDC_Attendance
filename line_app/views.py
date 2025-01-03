from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from django.contrib.auth.models import User
from line_app.models import UserProfile
from linebot.models import (
    MessageEvent, FollowEvent, PostbackEvent, TextMessage,
    PostbackAction, TextSendMessage, TemplateSendMessage, ButtonsTemplate
)
from django.shortcuts import render


line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler("c9dcfe2c8294dae35286dd84d69cfc21")


def register(request):
    return render(request, 'line_app/register.html')


@handler.add(FollowEvent)
def handle_follow(event):
    try:
        line_id = event.source.user_id
        profile = line_bot_api.get_profile(line_id)

        # Debugging logs
        print(f"Received follow event from LINE ID: {line_id}")
        print(f"Profile: {profile.display_name}, {profile.picture_url}, {profile.status_message}")

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
        print("UserProfile updated or created successfully.")
    except Exception as e:
        print(f"Error in handle_follow: {e}")


@csrf_exempt
def callback(request):
    if request.method == "POST":
        # get X-Line-Signature header value
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        domain = request.META['HTTP_HOST']
        body = request.body.decode('utf-8')

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            return HttpResponseBadRequest()
        return HttpResponse()
    else:
        return HttpResponseBadRequest()
