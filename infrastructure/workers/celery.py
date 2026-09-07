"""
Celery application configuration for background processing.
"""

from __future__ import annotations

import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("customer_data_platform")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def health_check(self):
    """Simple worker health-check task."""
    return {
        "status": "ok",
        "worker": self.request.hostname,
    }