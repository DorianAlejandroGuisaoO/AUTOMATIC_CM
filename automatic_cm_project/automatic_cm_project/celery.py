# automatic_cm/celery.py (NUEVO - créalo)
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatic_cm.settings')

app = Celery('automatic_cm_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()