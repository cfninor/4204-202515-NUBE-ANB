from celery import Celery
from config import config

celery = Celery(__name__, broker=str(config.RABBIT_URL))
celery.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
)

celery.autodiscover_tasks(["app.workers"])
