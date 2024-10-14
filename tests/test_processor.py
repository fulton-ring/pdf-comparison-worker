from worker.types import ParseJob
from worker.processor import process_remote_document


def test_process_remote_document():
    request = ParseJob(
        job_id="test",
        output_format="md",
        source_file="uploads/28337a5b-c423-42fd-9b93-4d5f4fa81dd3.pdf",
    )

    process_remote_document(request)
    assert False
