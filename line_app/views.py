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
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)


def register(request):
    return render(request, 'line_app/register.html')


@handler.add(FollowEvent)
def handle_follow(event):
    line_id = event.source.user_id
    profile = line_bot_api.get_profile(line_id)
    profile_exists = UserProfile.objects.filter(line_id=line_id).count() != 0
    if profile_exists:
        user_profile = UserProfile.objects.get(line_id=line_id)
        user_profile.line_name = profile.display_name
        user_profile.line_picture_url = profile.picture_url
        user_profile.line_status_message = profile.status_message
        user_profile.unfollow = False
        user_profile.save()
    else:
        user_profile = UserProfile(
            line_id=line_id,
            line_name=profile.display_name,
            line_picture_url=profile.picture_url,
            line_status_message=profile.status_message,
        )
        user_profile.save()


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
