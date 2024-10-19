from celery import Celery

from worker.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from worker.processor import process_remote_document
from worker.types import ParseJob

app = Celery(
    "worker",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
)


@app.task
def process_pdf(request: ParseJob):
    print("processing pdf:", request.source_file)
    process_remote_document(request)
    return {"result": "success"}
