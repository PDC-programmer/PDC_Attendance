import pandas as pd
import datetime

# อ่านไฟล์ Excel
df = pd.read_excel('pt_info_pos.xlsx', sheet_name="pt_info")
df_erp = pd.read_excel('pt_info_erp.xlsx', sheet_name="pt_info")
# สร้าง DataFrame ว่างเปล่าสำหรับเก็บผลลัพธ์ทั้งหมด
# data = pd.DataFrame(df)
print(df)
print(df_erp)
