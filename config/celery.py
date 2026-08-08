import os
from celery import Celery

# Set default Django settings module for celery CLI
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('smartops')

# Read config from Django settings namespace 'CELERY'
# e.g., CELERY_BROKER_URL in settings.py becomes BROKER_URL for Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps (looks for tasks.py)
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery worker functionality."""
    print(f'Celery Request: {self.request!r}')
