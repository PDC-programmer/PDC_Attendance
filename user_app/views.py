# import datetime
# import json
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from .serializers import *
# from django.shortcuts import render
# from django.shortcuts import get_object_or_404
# from rest_framework.decorators import api_view, parser_classes, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.parsers import MultiPartParser, FormParser
# from django.http import HttpResponse
# from weasyprint import HTML, CSS  # Error when using pdf comment for a while
# from django.template.loader import render_to_string
# import os
# from dotenv import load_dotenv
# from django.templatetags.static import static
# from django.db.models import Prefetch, Max  # Import Prefetch
# from django.db import transaction
# from django.core.exceptions import ValidationError
# from django.db import connections
# import pymysql
# from django.utils.timezone import now  # To get the current datetime
# from datetime import datetime, timedelta
#
# # Load .env file
# load_dotenv()
#
# @api_view(['POST'])
# def create_patient_both_db(request):
#     """
#     API to create a new patient in the old_db and then in the new pt_info (pdcmini_erp).
#     """
#     data = request.data  # Patient data from the request body
#
#     # Connection to old_db using pymysql
#     old_db_connection = pymysql.connect(
#         host=os.getenv("OLD_DB_HOST"),
#         user=os.getenv("OLD_DB_USER"),
#         password=os.getenv("OLD_DB_PASSWORD"),
#         database=os.getenv("OLD_DB_DATABASE"),
#         port=3306,
#         charset='utf8mb4',
#         cursorclass=pymysql.cursors.DictCursor
#     )
#
#     try:
#         with transaction.atomic():  # Ensures both operations are treated as a single transaction
#             # Generate a new unique pt_id for old_db
#             with old_db_connection.cursor() as cursor:
#                 cursor.execute("SELECT MAX(pt_id) AS max_pt_id FROM pt_info")
#                 result = cursor.fetchone()
#                 last_pt_id = result['max_pt_id'] if result['max_pt_id'] else 0
#                 new_pt_id = last_pt_id + 1
#
#                 # Insert new patient into old_db
#                 insert_query = """
#                     INSERT INTO pt_info (pt_id, pt_fname, pt_lname, mobile_no, brc_id, insert_usr_id, date_of_insert)
#                     VALUES (%s, %s, %s, %s, %s, %s, %s)
#                 """
#                 cursor.execute(insert_query, [
#                     new_pt_id,
#                     data.get('pt_fname'),
#                     data.get('pt_lname'),
#                     data.get('mobile_no'),
#                     data.get('brc_id'),
#                     62,  # Hardcoded user ID
#                     now().strftime('%Y-%m-%d %H:%M:%S')  # Current datetime formatted for MySQL
#                 ])
#                 old_db_connection.commit()
#
#             # Validate the branch in the default database
#             try:
#                 brc = BsnBranch.objects.using('default').get(brc_id=data.get('brc_id'))
#             except BsnBranch.DoesNotExist:
#                 return Response({"error": "Branch not found."}, status=status.HTTP_400_BAD_REQUEST)
#
#             # Insert new patient into the default database (new pt_info)
#             PtInfo.objects.using('default').create(
#                 pt_id=new_pt_id,
#                 pt_fname=data.get('pt_fname'),
#                 pt_lname=data.get('pt_lname'),
#                 mobile_no=data.get('mobile_no'),
#                 line_id=data.get('line_id'),
#                 brc_id=brc,
#                 insert_usr_id=62,  # Hardcoded user ID
#                 date_of_insert=now(),  # Django timezone-aware datetime
#             )
#
#             return Response(
#                 {"message": "Patient created successfully", "pt_id": new_pt_id},
#                 status=status.HTTP_201_CREATED
#             )
#
#     except Exception as e:
#         old_db_connection.rollback()  # Rollback the transaction in old_db in case of failure
#         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
#
#     finally:
#         old_db_connection.close()
#
#
# @api_view(['POST'])
# def update_verified_pt_info(request, pt_id):
#     """
#     API to update patient info in old_db using pymysql. (and default db)
#     Also updates the 'verify' field to 1 in the default database to mark it as verified.
#     """
#     # Extract data from the request
#     data = request.data
#
#     # Database connection to old_db using pymysql
#     old_db_connection = pymysql.connect(
#         host=os.getenv("OLD_DB_HOST"),
#         user=os.getenv("OLD_DB_USER"),
#         password=os.getenv("OLD_DB_PASSWORD"),
#         database=os.getenv("OLD_DB_DATABASE"),
#         port=3306,
#         charset='utf8mb4',
#         cursorclass=pymysql.cursors.DictCursor
#     )
#
#     try:
#         # Raw SQL query for updating the patient info in old_db
#         update_query = """
#             UPDATE pt_info
#             SET pt_fname = %s,
#                 pt_lname = %s,
#                 mobile_no = %s,
#                 brc_id = %s,
#                 email_addr = %s,
#                 pt_type = %s,
#                 pt_hn = %s,
#                 pt_ohn = %s,
#                 pt_pin = %s,
#                 pt_photo = %s,
#                 pt_nname = %s,
#                 pt_gender = %s,
#                 marital_status = %s,
#                 date_of_birth = %s,
#                 mobile_no = %s,
#                 email_addr = %s,
#                 addr_line1 = %s,
#                 addr_prov = %s,
#                 addr_city = %s,
#                 addr_suburb = %s,
#                 addr_zipcode = %s,
#                 pre_addr_line1 = %s,
#                 pre_addr_prov = %s,
#                 pre_addr_city = %s,
#                 pre_addr_suburb = %s,
#                 pre_addr_zipcode = %s,
#                 occ_id = %s,
#                 pt_occ = %s,
#                 pt_income = %s,
#                 kchn_id = %s,
#                 trv_id = %s,
#                 dr_id = %s,
#                 line_id = %s,
#                 approve_status = %s,
#                 device_no = %s,
#                 pt_passcode = %s,
#                 insert_usr_id = %s,
#                 date_of_insert = %s,
#                 update_usr_id = %s,
#                 date_of_update = %s,
#                 delete_usr_id = %s,
#                 date_of_delete = %s
#             WHERE pt_id = %s
#         """
#
#         # Extract values dynamically from data
#         values = [
#             data.get('pt_fname'),
#             data.get('pt_lname'),
#             data.get('mobile_no'),
#             data.get('brc_id'),
#             data.get('email_addr'),
#             data.get('pt_type'),
#             data.get('pt_hn'),
#             data.get('pt_ohn'),
#             data.get('pt_pin'),
#             data.get('pt_photo'),
#             data.get('pt_nname'),
#             data.get('pt_gender'),
#             data.get('marital_status'),
#             data.get('date_of_birth'),
#             data.get('mobile_no'),
#             data.get('email_addr'),
#             data.get('addr_line1'),
#             data.get('addr_prov'),
#             data.get('addr_city'),
#             data.get('addr_suburb'),
#             data.get('addr_zipcode'),
#             data.get('pre_addr_line1'),
#             data.get('pre_addr_prov'),
#             data.get('pre_addr_city'),
#             data.get('pre_addr_suburb'),
#             data.get('pre_addr_zipcode'),
#             data.get('occ_id'),
#             data.get('pt_occ'),
#             data.get('pt_income'),
#             data.get('kchn_id'),
#             data.get('trv_id'),
#             data.get('dr_id'),
#             data.get('line_id'),
#             data.get('approve_status'),
#             data.get('device_no'),
#             data.get('pt_passcode'),
#             data.get('insert_usr_id'),
#             data.get('date_of_insert'),
#             data.get('update_usr_id'),
#             now().strftime('%Y-%m-%d %H:%M:%S'),  # Current datetime formatted for MySQL
#             data.get('delete_usr_id'),
#             data.get('date_of_delete'),
#             pt_id  # For the WHERE clause
#         ]
#
#         # Execute the update query on old_db
#         with old_db_connection.cursor() as cursor:
#             cursor.execute(update_query, values)
#         old_db_connection.commit()  # Commit the transaction
#
#         madical_fees = request.data.pop('madical_fees', [])
#         congenital_diseases = request.data.pop('congenital_diseases', [])
#         try:
#             # Attempt to retrieve the PtInfo record
#             pt_info = PtInfo.objects.get(pt_id=pt_id)
#             # madical_fees = request.data.pop('formData.madical_fees', [])
#             serializer = PtInfoSerializer(pt_info, data=request.data)
#             operation = "updated"
#         except PtInfo.DoesNotExist:
#             return Response(
#                 {"message": f"Patient not found."},
#                 status=status.HTTP_404_NOT_FOUND
#             )
#
#         if serializer.is_valid():
#             # Set the verify field to 1
#             pt_info = serializer.save()
#             pt_info.date_of_update = now()
#             pt_info.verify = 1  # Set the verify field to 1
#             pt_info.save()  # Save the changes to the database
#
#             # Handle congenital diseases
#             PtInfoCongenitalDisease.objects.filter(pt_id=pt_info).delete()  # Clear exists record
#             for congenital_disease in congenital_diseases:
#                 try:
#                     # Get SysPtCongenitalDisease instance by cd_id
#                     sys_pt_congenital_disease = SysPtCongenitalDisease.objects.get(cd_id=congenital_disease['cd_id'])
#                     # Create a new PtInfoCongenitalDisease record
#                     PtInfoCongenitalDisease.objects.update_or_create(
#                         pt_id=pt_info,  # Link to the PtInfo record
#                         cd_id=sys_pt_congenital_disease,  # Use the SysPtCongenitalDisease instance
#                         defaults={
#                             'specify_val': congenital_disease.get('specify_val', None)
#                         }
#                     )
#                 except SysPtCongenitalDisease.DoesNotExist:
#                     # Handle the case where the SysPtCongenitalDisease is not found
#                     return Response(
#                         {"message": f"SysPtCongenitalDisease with cd_id {congenital_disease['cd_id']} not found."},
#                         status=status.HTTP_404_NOT_FOUND
#                     )
#             # Handle medical fees
#             PtInfoMadicalFee.objects.filter(pt_id=pt_info).delete()  # Clear existing records
#             for madical_fee in madical_fees:
#                 try:
#                     # Get SysPtMadicalFee instance by mf_id
#                     sys_madical_fee = SysPtMadicalFee.objects.get(mf_id=madical_fee['mf_id'])
#                     # Create a new PtInfoMadicalFee record
#                     PtInfoMadicalFee.objects.update_or_create(
#                         pt_id=pt_info,
#                         mf_id=sys_madical_fee,
#                         defaults={
#                             'specify_val': madical_fee.get('specify_val', None)
#                         }
#                     )
#                 except SysPtMadicalFee.DoesNotExist:
#                     return Response(
#                         {"message": f"SysPtMadicalFee with mf_id {madical_fee['mf_id']} not found."},
#                         status=status.HTTP_404_NOT_FOUND
#                     )
#
#         return Response(
#             {
#                 "message": f"Patient info with pt_id {pt_id} has been updated in both databases and marked as verified.",
#                 "updated_data": {
#                     "pt_id": pt_id,
#                     "pt_fname": data.get("pt_fname"),
#                     "pt_lname": data.get("pt_lname"),
#                     "mobile_no": data.get("mobile_no"),
#                     "brc_id": data.get("brc_id"),
#                     "email_addr": data.get("email_addr"),
#                     "addr_line1": data.get("addr_line1"),
#                     "addr_prov": data.get("addr_prov"),
#                     "addr_city": data.get("addr_city"),
#                     "addr_suburb": data.get("addr_suburb"),
#                     "addr_zipcode": data.get("addr_zipcode"),
#                     "pre_addr_line1": data.get("pre_addr_line1"),
#                     "pre_addr_prov": data.get("pre_addr_prov"),
#                     "pre_addr_city": data.get("pre_addr_city"),
#                     "pre_addr_suburb": data.get("pre_addr_suburb"),
#                     "pre_addr_zipcode": data.get("pre_addr_zipcode"),
#                     # Add more fields if necessary
#                 }
#             },
#             status=status.HTTP_200_OK
#         )
#
#     except Exception as e:
#         # Handle errors
#         return Response(
#             {"error": f"An error occurred: {str(e)}"},
#             status=status.HTTP_400_BAD_REQUEST
#         )
#
#     finally:
#         old_db_connection.close()  # Ensure the connection is closed