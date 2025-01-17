from datetime import datetime, timedelta, time
from django.conf import settings


def calculate_working_hours(start_datetime, end_datetime):
    # Define working hours
    morning_start = time(9, 0)  # 9:00 AM
    morning_end = time(12, 0)  # 12:00 PM
    afternoon_start = time(13, 0)  # 1:00 PM
    afternoon_end = time(18, 0)  # 6:00 PM

    total_hours = 0

    current = start_datetime
    while current.date() <= end_datetime.date():
        # Set the current day's morning and afternoon periods
        work_morning_start = datetime.combine(current.date(), morning_start)
        work_morning_end = datetime.combine(current.date(), morning_end)
        work_afternoon_start = datetime.combine(current.date(), afternoon_start)
        work_afternoon_end = datetime.combine(current.date(), afternoon_end)

        # Calculate effective working hours for the morning period
        if current <= work_morning_end:
            effective_start = max(current, work_morning_start)
            effective_end = min(end_datetime, work_morning_end)
            if effective_start < effective_end:
                total_hours += (effective_end - effective_start).total_seconds() / 3600

        # Calculate effective working hours for the afternoon period
        if current <= work_afternoon_end:
            effective_start = max(current, work_afternoon_start)
            effective_end = min(end_datetime, work_afternoon_end)
            if effective_start < effective_end:
                total_hours += (effective_end - effective_start).total_seconds() / 3600

        # Move to the next day
        current = datetime.combine(current.date() + timedelta(days=1), time.min)

    return total_hours
