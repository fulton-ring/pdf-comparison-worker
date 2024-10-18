from worker.types import ParseJob
from worker.processor import process_remote_document, parse_markdown_page


def test_process_remote_document():
    request = ParseJob(
        job_id="test",
        output_format="md",
        source_file="uploads/28337a5b-c423-42fd-9b93-4d5f4fa81dd3.pdf",
    )

    process_remote_document(request)
    assert False


def test_parse_markdown_page():
    page = """
```markdown
# hello
## world
```
"""
    assert parse_markdown_page(page) == [
        """# hello
## world"""
    ]


def test_parse_markdown_page_no_markdown():
    page = """
```
# hello
## world
```
"""
    assert parse_markdown_page(page) == [
        """# hello
## world"""
    ]
