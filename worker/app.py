from celery import Celery

from worker.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from worker.processor import process_remote_document, update_status
from worker.types import ParseJob

app = Celery(
    "worker",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
)


@app.task
def process_pdf(request: dict):
    job = ParseJob(**request)

    try:
        print("processing pdf:", job.source_file)
        process_remote_document(job)
        update_status(job.job_id, "completed")
        return {"result": "success", "error": None}
    except Exception as e:
        print("error processing pdf:", e)
        update_status(job.job_id, f"errored: {str(e)}")
        return {"result": "error", "error": str(e)}
