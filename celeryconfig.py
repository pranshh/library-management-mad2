from celery.schedules import crontab

beat_schedule = {
    'daily-reminder': {
        'task': 'tasks.daily_reminders',
        'schedule': crontab(minute='*'),
    }
}

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True