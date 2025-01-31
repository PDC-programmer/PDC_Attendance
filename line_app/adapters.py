from allauth.account.adapter import DefaultAccountAdapter


class MyCustomAccountAdapter(DefaultAccountAdapter):

    def save_user(self, request, user, form, commit=True):
        """
        บันทึก User โดยไม่บันทึกค่า first_name และ last_name หาก Sign Up มาจาก Line
        """
        # ตรวจสอบว่า Sign Up มาจาก Line หรือไม่
        is_line_signup = request.session.get('socialaccount_provider') == 'line'

        try:
            # รับข้อมูลจากฟอร์ม
            data = form.cleaned_data
            email = data.get("email")
            username = data.get("username")
            user.email = email
            user.username = username

            # ถ้าไม่ใช่ Line ให้บันทึก first_name และ last_name
            if not is_line_signup:
                first_name = data.get("first_name")
                last_name = data.get("last_name")
                user.first_name = first_name or ''
                user.last_name = last_name or ''

            # ตั้งรหัสผ่าน
            if "password1" in data:
                user.set_password(data["password1"])
            elif "password" in data:
                user.set_password(data["password"])
            else:
                user.set_unusable_password()

            if commit:
                user.save()

        except Exception as e:
            print(f"Error saving user: {e}")

        return user
