"""
Celery configuration for 49FlashMoney platform.
Handles async tasks: notifications, reconciliation, game processing.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lottery.settings.development')

app = Celery('lottery')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is running."""
    print(f'Request: {self.request!r}')
