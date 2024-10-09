from celery import Celery
from fastapi import FastAPI
from pydantic import BaseModel

# app = FastAPI()

app = Celery(
    "worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)


class ParseRequest(BaseModel):
    pdf_path: str


@app.task
def process_pdf(pdf_path: str):
    # TODO: process pdf
    print("processing pdf:", pdf_path)
    return "processed"


# @app.post("/parse")
# async def parse_route(pdf_request: ParseRequest):
#     pdf_path = pdf_request.pdf_path
#     task = process_pdf.delay(pdf_path)
#     return {"task_id": task.id}


# NOTE: run with `fastapi dev app.py`
