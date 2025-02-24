import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatMessage


@csrf_exempt
def oho_chat_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            sender = data.get('sender', 'Unknown')
            receiver = data.get('receiver', 'Unknown')
            message = data.get('message', '')
            message_type = data.get('type', 'received')  # ค่าจะเป็น 'sent' หรือ 'received'

            # บันทึกข้อความลง Database
            ChatMessage.objects.create(
                sender=sender,
                receiver=receiver,
                message=message,
                message_type=message_type
            )

            return JsonResponse({'status': 'success', 'message': 'Message received'}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
