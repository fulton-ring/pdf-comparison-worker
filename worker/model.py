from typing import Optional, List, Dict

from transformers import AutoProcessor, AutoModel
from qwen_vl_utils import process_vision_info
import torch

MODEL_CACHE_PATH = "/model"
PROCESSOR_CACHE_PATH = "/processor"
MODEL_NAME = "Qwen/Qwen2-VL-7B-Instruct-AWQ"


def get_model():
    import os
    from transformers import Qwen2VLForConditionalGeneration

    return Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_NAME,
        # torch_dtype="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
        device_map="auto",
        # device_map="cuda:0",
        token=os.environ["HF_TOKEN"],
        cache_dir=MODEL_CACHE_PATH,
    )


def get_processor():
    from transformers import AutoProcessor

    return AutoProcessor.from_pretrained(
        MODEL_NAME,
        # min_pixels=min_pixels,
        # max_pixels=max_pixels,
        cache_dir=PROCESSOR_CACHE_PATH,
    )


# messages = [
#     {
#         "role": "user",
#         "content": [
#             {
#                 "type": "image",
#                 "image": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen-VL/assets/demo.jpeg",
#             },
#             {"type": "text", "text": "Describe this image."},
#         ],
#     }
# ]


def run_inference(
    messages: List[dict],  # List[InferenceMessage]
    processor: AutoProcessor,
    model: AutoModel,
) -> List[str]:
    # Preprocess the inputs
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    image_inputs, video_inputs = process_vision_info(messages)

    # Preparation for inference
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
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
