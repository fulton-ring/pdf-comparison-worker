from celery import Celery
from pydantic import BaseModel

from worker.config import REDIS_HOST, REDIS_PORT, REDIS_DB

# app = FastAPI()

app = Celery(
    "worker",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
)


class ParseRequest(BaseModel):
    pdf_path: str


@app.task
def process_pdf(pdf_path: str):
    # TODO: process pdf
    print("processing pdf:", pdf_path)
    return "processed"
