import pymysql
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime
from .models import BsnStaff, User, BsnBranch
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator


# ฟังก์ชันเชื่อมต่อ MySQL โดยใช้ pymysql
def get_mysql_connection():
    return pymysql.connect(
        host=settings.SOURCE_DB_HOST,
        user=settings.SOURCE_DB_USER,
        password=settings.SOURCE_DB_PASSWORD,
        database=settings.SOURCE_DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


# ฟังก์ชันดึง `staff_id` ล่าสุดจากฐานข้อมูล pymysql แล้วเพิ่มขึ้น 1
def get_next_staff_id():
    connection = get_mysql_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT MAX(staff_id) AS max_staff_id FROM bsn_staff")
        result = cursor.fetchone()
        max_staff_id = result["max_staff_id"] if result["max_staff_id"] else 0
    connection.close()
    return max_staff_id + 1


@login_required(login_url="log-in")
def manage_staff(request, staff_id=None):
    """ เพิ่ม หรือ แก้ไขพนักงานในหน้าเดียวกัน """
    if request.method == "POST":
        staff_code = request.POST.get("staff_code")
        staff_pname = request.POST.get("staff_pname")
        staff_fname = request.POST.get("staff_fname")
        staff_lname = request.POST.get("staff_lname")
        staff_fname_en = request.POST.get("staff_fname_en")
        staff_lname_en = request.POST.get("staff_lname_en")
        staff_department = request.POST.get("staff_department")
        staff_title = request.POST.get("staff_title")
        brc_id = request.POST.get("brc_id")
        mng_staff_code = request.POST.get("mng_staff_id")  # รับค่าเป็น staff_code
        staff_type = request.POST.get("staff_type")
        group_id = request.POST.get("group_id")
        brc_chkin_status = request.POST.get("brc_chkin_status")

        # ตรวจสอบและแปลงค่าว่างเป็น None ก่อนบันทึก
        date_of_start = request.POST.get("date_of_start")
        date_of_start = date_of_start if date_of_start else None  # ถ้าค่าว่างให้เป็น None

        date_of_resign = request.POST.get("date_of_resign")
        date_of_resign = date_of_resign if date_of_resign else None  # ถ้าค่าว่างให้เป็น None

        insert_usr = BsnStaff.objects.filter(django_usr_id=request.user.id).first()

        try:
            brc_instance = BsnBranch.objects.get(id=brc_id)
        except BsnBranch.DoesNotExist:
            return JsonResponse({"error": "ไม่พบข้อมูลสาขา"}, status=400)

        try:
            group_instance = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return JsonResponse({"error": "ไม่พบข้อมูลกลุ่มพนักงาน"}, status=400)

        # แปลง staff_code เป็น staff_id
        mng_staff = BsnStaff.objects.filter(staff_code=mng_staff_code).first()
        mng_staff_id = mng_staff.staff_id if mng_staff else None

        if staff_id:  # กรณีแก้ไข
            staff = BsnStaff.objects.get(staff_id=staff_id)
            staff.staff_code = staff_code
            staff.staff_pname = staff_pname
            staff.staff_fname = staff_fname
            staff.staff_lname = staff_lname
            staff.staff_fname_en = staff_fname_en
            staff.staff_lname_en = staff_lname_en
            staff.staff_department = staff_department
            staff.staff_title = staff_title
            staff.brc_id = brc_instance
            staff.mng_staff_id = mng_staff_id
            staff.staff_type = staff_type
            staff.date_of_start = date_of_start
            staff.group = group_instance
            staff.date_of_update = datetime.now()
            staff.brc_chkin_status = brc_chkin_status
            staff.date_of_resign = date_of_resign
            staff.save()
            message = "อัปเดตข้อมูลพนักงานสำเร็จ!"

        else:  # กรณีเพิ่มใหม่
            new_staff_id = get_next_staff_id()
            staff = BsnStaff.objects.create(
                staff_id=new_staff_id,
                staff_code=staff_code,
                staff_pname=staff_pname,
                staff_fname=staff_fname,
                staff_lname=staff_lname,
                staff_fname_en=staff_fname_en,
                staff_lname_en=staff_lname_en,
                staff_department=staff_department,
                staff_title=staff_title,
                brc_id=brc_instance,
                mng_staff_id=mng_staff_id,
                staff_type=staff_type,
                date_of_start=date_of_start,
                insert_usr_id=62,
                date_of_insert=datetime.now(),
                group=group_instance
            )
            message = "เพิ่มพนักงานสำเร็จ!"

        # อัปเดตข้อมูลไปยัง MySQL ผ่าน PyMySQL
        connection = get_mysql_connection()
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO bsn_staff (staff_id, staff_code, staff_pname, staff_fname, staff_lname, staff_fname_en, 
                                   staff_lname_en, staff_department, staff_title, brc_id, mng_staff_id, staff_type,
                                   date_of_start, date_of_resign, insert_usr_id, date_of_insert) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                staff_code = VALUES(staff_code),
                staff_pname = VALUES(staff_pname),
                staff_fname = VALUES(staff_fname),
                staff_lname = VALUES(staff_lname),
                staff_fname_en = VALUES(staff_fname_en),
                staff_lname_en = VALUES(staff_lname_en),
                staff_department = VALUES(staff_department),
                staff_title = VALUES(staff_title),
                brc_id = VALUES(brc_id),
                mng_staff_id = VALUES(mng_staff_id),
                staff_type = VALUES(staff_type),
                date_of_start = VALUES(date_of_start),
                date_of_resign = VALUES(date_of_resign),
                update_usr_id = %s,
                date_of_update = NOW()
            """
            cursor.execute(sql, (
                staff.staff_id, staff_code, staff_pname, staff_fname, staff_lname, staff_fname_en, staff_lname_en,
                staff_department, staff_title, brc_id,
                mng_staff_id if mng_staff_id is not None else None,  # ถ้า `None` ให้เก็บ `NULL`
                staff_type, date_of_start if date_of_start else None,  # ถ้า `None` ให้เก็บ `NULL`
                date_of_resign if date_of_resign else None,  # ✅ รองรับ `date_of_resign`
                62, datetime.now(),
                62  # update user id
            ))
            connection.commit()

        return JsonResponse({"message": message}, status=200)

    # ดึงข้อมูลพนักงานเมื่อเป็นการแก้ไข
    staff = BsnStaff.objects.get(staff_id=staff_id) if staff_id else None

    if staff is not None:
        manager = BsnStaff.objects.filter(staff_id=staff.mng_staff_id).first()
        staff.mng_staff_code = manager.staff_code if manager else ""

    branches = BsnBranch.objects.all()
    groups = Group.objects.filter(name__in=["CN", "CN2", "OP"])
    return render(request, "user_app/manage_staff.html", {
        "staff": staff,
        "branches": branches,
        "groups": groups
    })


@login_required(login_url="log-in")
def get_staff_codes(request):
    """ API สำหรับดึงรหัสพนักงานเพื่อใช้ใน Autocomplete """
    query = request.GET.get("q", "").strip()

    if query:
        staff_list = list(
            BsnStaff.objects.filter(staff_type="Manager", date_of_resign__isnull=True, staff_code__icontains=query)[:10]  # จำกัดผลลัพธ์ 10 รายการ
            .values("staff_code", "staff_fname", "staff_lname")
        )
    else:
        staff_list = []

    return JsonResponse(staff_list, safe=False)


@login_required(login_url="log-in")
def staff_list(request):
    """ แสดงรายการพนักงานเฉพาะเมื่อมีการค้นหา """
    search_query = request.GET.get("search", "").strip()
    staff_type_filter = request.GET.get("staff_type", "")

    staffs = BsnStaff.objects.none()  # ค่าเริ่มต้นให้เป็น None (ไม่แสดงข้อมูล)

    if search_query or staff_type_filter:  # แสดงเฉพาะเมื่อมีการค้นหาหรือกรองข้อมูล
        staffs = BsnStaff.objects.all().order_by('-date_of_insert').values()

        # ค้นหาด้วย staff_code, ชื่อ หรือ นามสกุล
        if search_query:
            staffs = staffs.filter(
                staff_code__icontains=search_query
            ) | staffs.filter(
                staff_fname__icontains=search_query
            ) | staffs.filter(
                staff_lname__icontains=search_query
            )

        # กรองประเภทพนักงาน (Staff หรือ Manager)
        if staff_type_filter:
            staffs = staffs.filter(staff_type=staff_type_filter)

    # ใช้ Paginator แบ่งหน้า (กำหนดให้แสดง 10 รายการต่อหน้า)
    paginator = Paginator(staffs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "user_app/staff_list.html", {
        "staffs": staffs,
        "search_query": search_query,
        "staff_type_filter": staff_type_filter,
        "page_obj": page_obj,
    })
