import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatMessage
from django.utils.timezone import datetime


@csrf_exempt
def oho_chat_webhook(request):
    if request.method == 'POST':
        try:
            # แปลง JSON ที่รับมา
            data = json.loads(request.body.decode('utf-8'))

            print(data)

            # ตรวจสอบว่ามี event ที่เป็น message หรือไม่
            events = data.get('events', [])
            if not events:
                return JsonResponse({'status': 'error', 'message': 'No events found'}, status=400)

            for event in events:
                if event.get('type') == 'message':  # ตรวจสอบว่าเป็นข้อความ
                    message_data = event.get('message', {})
                    source_data = event.get('source', {})

                    sender = source_data.get('userId', 'Unknown')  # ดึง userId ของผู้ส่ง
                    message_text = message_data.get('text', '')  # ดึงข้อความที่ส่งมา
                    timestamp = event.get('timestamp', None)  # ดึง timestamp
                    message_type = message_data.get('type', 'text')  # ดึงประเภทข้อความ

                    # แปลง timestamp เป็น datetime
                    if timestamp:
                        timestamp = datetime.fromtimestamp(timestamp / 1000)  # Convert ms to s

                    # บันทึกลง Database
                    ChatMessage.objects.create(
                        sender=sender,
                        receiver=data.get('destination', 'Unknown'),  # รับปลายทางจาก JSON
                        message=message_text,
                        timestamp=timestamp,
                        message_type='received'
                    )

            return JsonResponse({'status': 'success', 'message': 'Messages processed'}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
