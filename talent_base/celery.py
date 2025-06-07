import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_base.settings')

app = Celery('talent_base')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Enable broker connection retries on startup (for Celery 6+)
app.conf.broker_connection_retry_on_startup = True

app.autodiscover_tasks()
