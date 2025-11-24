from celery import Celery
from config import config

celery = Celery(__name__, broker=str(config.RABBIT_URL))
celery.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
)
if config.RABBIT_URL.startswith("sqs"):
    celery.conf.broker_transport_options = {
        "region": "us-east-1",
        "visibility_timeout": 180,
        "wait_time_seconds": 20,
        "queue_name_prefix": "anb-",
    }

celery.autodiscover_tasks(["workers"])
