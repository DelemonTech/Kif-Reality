import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kif_realty.settings')

app = Celery('kif_realty')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
