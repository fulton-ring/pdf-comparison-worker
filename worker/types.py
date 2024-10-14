from pydantic import BaseModel


class ParseJob(BaseModel):
    job_id: str
    output_format: str
    source_file: str
