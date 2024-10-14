from celery import Celery

from worker.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from worker.types import ParseJob

app = Celery(
    "worker",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
)


@app.task
def process_pdf(request: ParseJob):
    # TODO: for each page in PDF, generate image
    # TODO: for each image, run OCR
    # TODO: for each OCR result, run layout detection
    # TODO: for each layout detection result, run table detection
    # TODO: for each table detection result, run table parsing
    # TODO: for each table parsing result, run cell comparison
    # TODO: update status as pages are processed
    # TODO: upload parsed pages to S3
    # TODO: upload final document to S3
    print("processing pdf:", request.source_file)
    return "processed"
