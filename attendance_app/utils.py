from datetime import datetime, timedelta, time
from django.conf import settings


def calculate_working_hours(start_datetime, end_datetime):
    # Define working hours
    work_start = datetime.combine(start_datetime.date(),
                                  datetime.strptime(settings.WORKING_HOURS_START, "%H:%M").time())
    work_end = datetime.combine(start_datetime.date(), datetime.strptime(settings.WORKING_HOURS_END, "%H:%M").time())

    total_hours = 0

    current = start_datetime
    while current.date() <= end_datetime.date():
        # Determine the effective work period for the current day
        effective_start = max(current, work_start)
        effective_end = min(end_datetime, work_end)

        if effective_start < effective_end:  # Only count valid working hours
            total_hours += (effective_end - effective_start).total_seconds() / 3600

        # Move to the next day
        current = datetime.combine(current.date() + timedelta(days=1), time.min)
        work_start = datetime.combine(current.date(), work_start.time())
        work_end = datetime.combine(current.date(), work_end.time())

    return total_hours
