# my_job_queue_endpoint.py
import fastapi

from modal.functions import FunctionCall
import modal

from worker.model import get_model

image = (
    modal.Image.debian_slim(python_version="3.10")
    .poetry_install_from_file("pyproject.toml", poetry_lockfile="poetry.lock")
    .pip_install(
        "transformers==4.45.*",
        # "opencv-python",
        "pymupdf",
        "qwen-vl-utils",
        "autoawq",  # NOTE: autoawq requires python 3.10
        "torchvision==0.19.*",
        "torch==2.4.*",
    )
    .run_function(
        get_model,
        secrets=[
            modal.Secret.from_name("huggingface"),
            modal.Secret.from_name("supabase"),
        ],
        gpu="A100",
    )
)

app = modal.App("pdf-comparison")
web_app = fastapi.FastAPI()


@app.function()
@modal.asgi_app()
def fastapi_app():
    return web_app


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("huggingface"),
        modal.Secret.from_name("supabase"),
    ],
    gpu="A100",
    container_idle_timeout=15,
)
def process_job(data):
    return {"result": data}


@web_app.post("/submit")
async def submit_job_endpoint(data):
    process_job = modal.Function.lookup("pdf-comparison", "process_job")

    call = process_job.spawn(data)
    return {"call_id": call.object_id}


@web_app.get("/result/{call_id}")
async def get_job_result_endpoint(call_id: str):
    function_call = FunctionCall.from_id(call_id)
    try:
        result = function_call.get(timeout=0)
    except modal.exception.OutputExpiredError:
        return fastapi.responses.JSONResponse(content="", status_code=404)
    except TimeoutError:
        return fastapi.responses.JSONResponse(content="", status_code=202)

    return result


# NOTE: should run this before serving to seed the model
@app.local_entrypoint()
def main():
    data = "my-data"

    # Submit the job to Modal
    process_job = modal.Function.lookup("pdf-comparison", "process_job")
    call = process_job.spawn(data)
    print(call.object_id)
