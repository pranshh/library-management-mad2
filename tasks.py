from workers import celery
from jinja2 import Template
from sending_mail import sending_mail
from models import Request, Ebook
from sqlalchemy import func
from datetime import datetime, timedelta


@celery.task()
def daily_reminders(email="pj@gmail.com", username="pj"):
    with open('./templates/daily_reminders.html','r') as f:
        template = Template(f.read())
    sending_mail(email, 'Daily Library Reminder', template.render(user=username), content="html")
    return f"Daily reminder sent to {username}"

@celery.task()
def monthly_report(email="librarian@iitm.in"):
    with open('./templates/monthly_report.html', 'r') as f:
        template = Template(f.read())
    
    # Get the first day of the previous month
    today = datetime.now()
    first_day_of_month = today.replace(day=1)
    last_month = first_day_of_month - timedelta(days=1)
    start_date = last_month.replace(day=1)
    
    # Calculate report data
    total_requests = Request.query.filter(Request.date_requested >= start_date, Request.date_requested < first_day_of_month).count()
    total_returns = Request.query.filter(Request.return_date >= start_date, Request.return_date < first_day_of_month).count()
    
    top_ebooks = (
        Request.query.with_entities(Ebook.ebook_name, func.count(Request.request_id).label('count'))
        .join(Ebook)
        .filter(Request.date_requested >= start_date, Request.date_requested < first_day_of_month)
        .group_by(Ebook.ebook_id)
        .order_by(func.count(Request.request_id).desc())
        .limit(5)
        .all()
    )

    context = {
        'month': last_month.strftime('%B %Y'),
        'total_requests': total_requests,
        'total_returns': total_returns,
        'top_ebooks': top_ebooks,
    }

    sending_mail(email, 'Monthly Library Report', template.render(**context), content="html")
    print("Monthly report sent successfully")  # Add this line
    return f"Monthly report sent to {email}"
