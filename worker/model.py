MODEL_CACHE_PATH = "/model"
PROCESSOR_CACHE_PATH = "/processor"
MODEL_NAME = "Qwen/Qwen2-VL-7B-Instruct-AWQ"

MODEL = None
PROCESSOR = None


def get_model():
    import os
    from transformers import Qwen2VLForConditionalGeneration

    global MODEL

    if MODEL is None:
        MODEL = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_NAME,
            torch_dtype="auto",
            # torch_dtype=torch.bfloat16,
            # attn_implementation="flash_attention_2",
            device_map="auto",
            # device_map="cuda:0",
            token=os.environ["HF_TOKEN"],
            cache_dir=MODEL_CACHE_PATH,
        )

    return MODEL


def download_model():
    model = get_model()
    model.save_pretrained(MODEL_CACHE_PATH)


def get_processor():
    from transformers import AutoProcessor

    global PROCESSOR

    if PROCESSOR is None:
        PROCESSOR = AutoProcessor.from_pretrained(
            MODEL_NAME,
            # min_pixels=min_pixels,
            # max_pixels=max_pixels,
            cache_dir=PROCESSOR_CACHE_PATH,
        )

        # PROCESSOR.save_pretrained(PROCESSOR_CACHE_PATH)

    return PROCESSOR


def process_vision_info(messages, images):
    processor = get_processor()
    model = get_model()

    # Preprocess the inputs
    text_prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    # Excepted output: '<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>Describe this image.<|im_end|>\n<|im_start|>assistant\n'

    # Preparation for inference
    inputs = processor(
        text=[text_prompt], images=images, padding=True, return_tensors="pt"
    )
    inputs = inputs.to("cuda")

    # Inference: Generation of the output
    output_ids = model.generate(**inputs, max_new_tokens=4096)
    generated_ids = [
        output_ids[len(input_ids) :]
        for input_ids, output_ids in zip(inputs.input_ids, output_ids)
    ]

    return processor.batch_decode(
        generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True
    )
