import modal

from worker.types import InferenceRequest


def download_model():
    from worker.model import get_model, MODEL_CACHE_PATH

    model = get_model()
    model.save_pretrained(MODEL_CACHE_PATH)


app = modal.App("pdf-comparison", secrets=[modal.Secret.from_name("huggingface")])

image = (
    modal.Image.debian_slim(python_version="3.10")
    # .poetry_install_from_file("pyproject.toml", poetry_lockfile="poetry.lock")
    .pip_install(
        "transformers==4.45.*",
        "pillow",
        # "opencv-python",
        # "pymupdf",
        "qwen-vl-utils",
        "autoawq",  # NOTE: autoawq requires python 3.10
        "torchvision==0.19.*",
        "torch==2.4.*",
        "fastapi[standard]==0.115.*",
        "pydantic==2.9.*",
    ).run_function(
        download_model,
        secrets=[
            modal.Secret.from_name("huggingface"),
            # modal.Secret.from_name("supabase"),
        ],
        gpu="A100",
    )
)


@app.cls(
    gpu="A100",
    timeout=60,
    container_idle_timeout=15,
    allow_concurrent_inputs=1,
    image=image,
    retries=0,
)
class Model:
    @modal.enter()
    def start_runtime(self):
        from worker.model import get_model, get_processor

        self._model = get_model()
        self._processor = get_processor()

    @modal.web_endpoint(method="POST", docs=True)
    def generate(self, request: InferenceRequest):
        from worker.model import run_inference
        import pydantic

        print(pydantic.__version__)
        print(request.model_dump(exclude_none=True))
        request_dict = request.model_dump(exclude_none=True)

        outputs = run_inference(
            messages=request_dict["messages"],
            processor=self._processor,
            model=self._model,
        )

        return {"outputs": outputs}
