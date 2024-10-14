MODEL_CACHE_PATH = "/model"
PROCESSOR_CACHE_PATH = "/processor"
MODEL_NAME = "Qwen/Qwen2-VL-7B-Instruct-AWQ"


def get_model():
    import os
    from transformers import Qwen2VLForConditionalGeneration

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_NAME,
        torch_dtype="auto",
        # torch_dtype=torch.bfloat16,
        # attn_implementation="flash_attention_2",
        device_map="auto",
        # device_map="cuda:0",
        token=os.environ["HF_TOKEN"],
        cache_dir=MODEL_CACHE_PATH,
    )

    model.save_pretrained(MODEL_CACHE_PATH)
    return model


def get_processor():
    from transformers import AutoProcessor

    processor = AutoProcessor.from_pretrained(
        "Qwen/Qwen2-VL-7B-Instruct-AWQ",
        # min_pixels=min_pixels,
        # max_pixels=max_pixels,
        cache_dir=PROCESSOR_CACHE_PATH,
    )

    processor.save_pretrained(PROCESSOR_CACHE_PATH)
    return processor
