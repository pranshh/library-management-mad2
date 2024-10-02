from celery import Celery
from flask import current_app

celery = Celery('application jobs')
celery.config_from_object('celeryconfig')

class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with current_app.app_context():
            return super().__call__(*args, **kwargs)
        
celery.Task = ContextTask