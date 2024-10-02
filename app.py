from flask import Flask
from flask_cors import CORS
from flask_security import Security, SQLAlchemyUserDatastore, hash_password
from flask_jwt_extended import JWTManager
from datetime import datetime
import workers
from celery.schedules import crontab
from flask_apscheduler import APScheduler
from api import api
from models import db
from datetime import timedelta
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
app.config.update(
    SECRET_KEY="abcdefghijklmnop",
    WTF_CSRF_ENABLED=False,
    SQLALCHEMY_DATABASE_URI='sqlite:///lib.sqlite3',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECURITY_PASSWORD_SALT='abcdefghijklmnop',
    SECURITY_TOKEN_AUTHENTICATION_HEADER='Authorization',
    SECURITY_TOKEN_AUTHENTICATION_KEY='Bearer',
    SECURITY_TOKEN_AUTHENTICATION_ENABLED=True,
    SECURITY_PASSWORD_HASH='bcrypt',
    JWT_SECRET_KEY="abcdfeghijklmnop",
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1),
    UPLOAD_FOLDER = 'uploads',
    MAX_CONTENT_LENGTH = 16*1024*1024,
    CORS_HEADERS='Content-Type',
    CELERY_BROKER_URL='redis://localhost:6379/1',
    CELERY_RESULT_BACKEND='redis://localhost:6379/2'
)

CORS(app, supports_credentials=True, origins=["http://localhost:8080"])

db.init_app(app)
api.init_app(app)

from models import User, Role, Section, Ebook, Request, Feedback


celery = workers.celery
app.app_context().push()

celery.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0'
)
celery.Task = workers.ContextTask
app.app_context().push()

from tasks import daily_reminders, monthly_report

datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, datastore)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def create_user():
    if not datastore.find_role("librarian"):
        datastore.create_role(name="librarian")

    # Ensure the librarian user exists
    if not datastore.find_user(email="librarian@iitm.in"):
        datastore.create_user(
            email="librarian@iitm.in",
            username="librarian",
            password=hash_password("librarian"),
            roles=["librarian"]
        )
    db.session.commit()

jwt = JWTManager(app)


@celery.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute='*'),
        daily_reminders.s(),
        name="daily reminder"
    )
    sender.add_periodic_task(
        crontab(minute='*'),
        monthly_report.s(),
        name="monthly report"
    )

def revoke_access(request_id):
    with app.app_context():
        req = Request.query.get(request_id)
        if req and req.status == 'granted':
            req.status = 'revoked'
            req.date_revoked = datetime.now()
            db.session.commit()

@scheduler.task('cron', id='revoke_expired_requests', hour='0')
def revoke_expired_requests():
    with app.app_context():
        expired_requests = Request.query.filter(
            Request.status == 'granted',
            Request.return_date <= datetime.now()
        ).all()
        for req in expired_requests:
            revoke_access(req.request_id)

SWAGGER_URL = '/api/docs'
API_URL = '/swagger.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "api.py"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)



# To serve the swagger.yaml file
from flask import send_from_directory
import os

@app.route('/swagger.yaml')
def send_static():
    return send_from_directory('.', 'swagger.yaml')

if __name__ == "__main__":  
    with app.app_context():
        db.create_all()
        create_user()
    app.run(debug=True)
    
# Run commands:
# celery -A app.celery worker -l info
# celery -A app.celery beat --max-interval 1 -l info
# mailhog
# python3 app.py
# npm run serve
# redis-server
# ~/go/bin/MailHog
# http://localhost:8025/