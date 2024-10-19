from typing import List, Literal, Optional
from pydantic import BaseModel


class ParseJob(BaseModel):
    job_id: str
    output_format: str
    source_file: str


class InferenceMessageContent(BaseModel):
    type: Literal["image", "text"]
    image: Optional[str] = None  # starts with data:image;base64,
    text: Optional[str] = None
    resized_height: Optional[int] = None
    resized_width: Optional[int] = None


class InferenceMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: List[InferenceMessageContent]


class InferenceRequest(BaseModel):
    messages: List[InferenceMessage]
