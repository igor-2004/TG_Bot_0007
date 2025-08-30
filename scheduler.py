# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
from db import cleanup_submissions_older_than
from config import MSK_UTC_OFFSET, DB_CLEANUP_DAYS

scheduler = BackgroundScheduler()

def daily_cleanup_job():
    deleted = cleanup_submissions_older_than(DB_CLEANUP_DAYS)
    print(f"[{datetime.utcnow().isoformat()}] DB cleanup executed. Deleted rows: {deleted}")

def start_scheduler():
    # Для запуска в 00:00 MSK (UTC = MSK - MSK_UTC_OFFSET)
    trigger_hour_utc = (24 - MSK_UTC_OFFSET) % 24
    trigger = CronTrigger(hour=trigger_hour_utc, minute=0, timezone=timezone.utc)
    scheduler.add_job(daily_cleanup_job, trigger)
    scheduler.start()
