# import pymysql
# from django.shortcuts import render, get_object_or_404
# from django.http import JsonResponse
# from django.utils.timezone import now
# from user_app.models import User, BsnStaff
# from django.views.decorators.csrf import csrf_exempt
# import json
# from django.conf import settings
#
#
# # ฟังก์ชันสำหรับซิงค์ข้อมูลไปยังฐานข้อมูลภายนอก
# def sync_staff_to_external_db(staff):
#     """
#     อัปเดตหรือสร้างข้อมูลพนักงานในฐานข้อมูลภายนอก
#     """
#     try:
#         # ตั้งค่าการเชื่อมต่อไปยังฐานข้อมูลภายนอก
#         external_db = pymysql.connect(
#             host=settings.EXTERNAL_DB_HOST,
#             user=settings.EXTERNAL_DB_USER,
#             password=settings.EXTERNAL_DB_PASSWORD,
#             database=settings.EXTERNAL_DB_NAME,
#             charset="utf8mb4",
#             cursorclass=pymysql.cursors.DictCursor
#         )
#
#         with external_db.cursor() as cursor:
#             # ตรวจสอบว่ามีพนักงานในฐานข้อมูลภายนอกหรือยัง
#             sql_check = "SELECT COUNT(*) as count FROM bsn_staff WHERE staff_id = %s"
#             cursor.execute(sql_check, (staff.staff_id,))
#             result = cursor.fetchone()
#
#             if result["count"] > 0:
#                 # อัปเดตข้อมูลพนักงานในฐานข้อมูลภายนอก
#                 sql_update = """
#                     UPDATE bsn_staff SET
#                         staff_code = %s,
#                         staff_fname = %s,
#                         staff_lname = %s,
#                         staff_department = %s,
#                         staff_title = %s,
#                         date_of_update = NOW()
#                     WHERE staff_id = %s
#                 """
#                 cursor.execute(sql_update, (
#                     staff.staff_code,
#                     staff.staff_fname,
#                     staff.staff_lname,
#                     staff.staff_department,
#                     staff.staff_title,
#                     staff.staff_id
#                 ))
#             else:
#                 # สร้างข้อมูลพนักงานใหม่ในฐานข้อมูลภายนอก
#                 sql_insert = """
#                     INSERT INTO bsn_staff (staff_id, staff_code, staff_fname, staff_lname, staff_department, staff_title, date_of_insert)
#                     VALUES (%s, %s, %s, %s, %s, %s, NOW())
#                 """
#                 cursor.execute(sql_insert, (
#                     staff.staff_id,
#                     staff.staff_code,
#                     staff.staff_fname,
#                     staff.staff_lname,
#                     staff.staff_department,
#                     staff.staff_title
#                 ))
#
#         external_db.commit()
#         external_db.close()
#         return True
#
#     except Exception as e:
#         print(f"❌ Error syncing to external DB: {e}")
#         return False
#
#
# @csrf_exempt
# def create_or_update_staff(request):
#     """
#     API สำหรับสร้างหรืออัปเดตพนักงานในระบบ พร้อมอัปเดตไปยังฐานข้อมูลภายนอก
#     """
#     if request.method == "POST":
#         try:
#             data = json.loads(request.body)
#
#             # ดึงข้อมูลจาก request
#             user_id = data.get("user_id")
#             staff_code = data.get("staff_code")
#             staff_fname = data.get("staff_fname")
#             staff_lname = data.get("staff_lname")
#             staff_department = data.get("staff_department")
#             staff_title = data.get("staff_title")
#
#             # ตรวจสอบว่าผู้ใช้มีอยู่ในระบบหรือไม่
#             user = get_object_or_404(User, id=user_id)
#
#             # ตรวจสอบว่ามีพนักงานอยู่ใน `BsnStaff` หรือยัง
#             staff, created = BsnStaff.objects.update_or_create(
#                 django_usr_id=user,
#                 defaults={
#                     "staff_code": staff_code,
#                     "staff_fname": staff_fname,
#                     "staff_lname": staff_lname,
#                     "staff_department": staff_department,
#                     "staff_title": staff_title,
#                     "date_of_update": now() if not created else None,
#                     "date_of_insert": now() if created else None
#                 }
#             )
#
#             # อัปเดตไปยังฐานข้อมูลภายนอก
#             sync_status = sync_staff_to_external_db(staff)
#
#             return JsonResponse({
#                 "message": "พนักงานถูกอัปเดตเรียบร้อยแล้ว" if not created else "สร้างพนักงานใหม่สำเร็จ",
#                 "sync_status": "Success" if sync_status else "Failed"
#             }, status=200)
#
#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=400)
#
#     return JsonResponse({"error": "Method not allowed"}, status=405)
