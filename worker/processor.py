import base64
import tempfile
import os
import io

# from anthropic import AsyncAnthropicBedrock, RateLimitError
import fitz
from PIL import Image
import requests

# import s3fs

from worker import clients, config
from worker.types import (
    InferenceMessage,
    InferenceMessageContent,
    ParseJob,
    InferenceRequest,
)


CONVERSTION_PROMPT = """
Convert this image of a page from a PDF into markdown.
Make sure the tables are valid markdown tables.
Do not include content that isn't part of the image.
Use ```markdown ...``` to format the markdown.
"""

CORRECT_PAGE_OVERLAP_PROMPT = """
Check if the current page starts with a table that continued from the previous page.
If it does, correct the current and previous pages.

Use ```markdown``` to format the markdown.
"""


def download_file(source: str, destination: str):
    supabase_client = clients.get_supabase_client()

    with open(destination, "wb+") as fp:
        res = supabase_client.storage.from_(
            config.SUPABASE_UPLOADS_BUCKET,
        ).download(source)
        fp.write(res)


def upload_file(source: str, destination: str):
    supabase_client = clients.get_supabase_client()

    with open(source, "rb") as fp:
        supabase_client.storage.from_(
            config.SUPABASE_JOBS_BUCKET,
        ).upload(destination, fp)


def call_inference_api(request: InferenceRequest):
    # TODO: add retries
    try:
        response = requests.post(
            config.INFERENCE_API_ENDPOINT, data=request.model_dump_json()
        )

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Error calling inference API:", e)
        raise e


def parse_markdown_page(page: str):
    markdown_blocks = []
    start_index = 0

    while True:
        new_start_index = page.find("```markdown", start_index)

        if new_start_index == -1:
            new_start_index = page.find("```", start_index)

        if new_start_index == -1:
            break  # No more markdown blocks found

        new_start_index = (
            page.find("\n", new_start_index) + 1
        )  # Move to the next line after the opening ```

        end_index = page.find("```", new_start_index)
        if end_index == -1:
            markdown_blocks.append(page[new_start_index:].strip())
            break  # No closing ```, use the rest of the page

        markdown_blocks.append(page[new_start_index:end_index].strip())
        start_index = end_index + 3  # Move past the closing ```

    return markdown_blocks


def convert_page_to_markdown(
    # image: Image.Image,
    image_base64_string: str,
):
    response = call_inference_api(
        request=InferenceRequest(
            messages=[
                InferenceMessage(
                    role="user",
                    content=[
                        InferenceMessageContent(
                            type="image",
                            image=image_base64_string,
                            # image=f"data:image;base64,{base64.b64encode(image.tobytes()).decode('utf-8')}",
                            # resized_height=image.height,
                            # resized_width=image.width,
                        ),
                        InferenceMessageContent(
                            type="text",
                            text=CONVERSTION_PROMPT,
                        ),
                    ],
                )
            ],
        )
    )

    return parse_markdown_page(response["outputs"][0])[0]


def correct_page_overlap(last_page: str, current_page: str):
    response = call_inference_api(
        request=InferenceRequest(
            messages=[
                InferenceMessage(
                    role="user",
                    content=[
                        InferenceMessageContent(
                            type="text", text=CORRECT_PAGE_OVERLAP_PROMPT
                        ),
                        InferenceMessageContent(
                            type="text", text=f"Last page: {last_page}"
                        ),
                        InferenceMessageContent(
                            type="text", text=f"Current page: {current_page}"
                        ),
                    ],
                )
            ],
        )
    )

    print("corrected_pages:", response["outputs"])
    corrected_pages = parse_markdown_page(response["outputs"][0])

    if len(corrected_pages) != 2:
        return last_page, current_page

    return corrected_pages[0], corrected_pages[1]


def convert_document(input_file_path: str):
    doc = fitz.open(input_file_path)
    last_page = None
    page_counter = 0

    for page in doc:
        pix = page.get_pixmap()  # type: ignore

        image = Image.open(io.BytesIO(pix.tobytes()))

        new_width = min(((image.width + 27) // 28) * 28, 16384)
        new_height = min(((image.height + 27) // 28) * 28, 16384)

        # pix = fitz.Pixmap(pix, new_width, new_height)

        # image = image.copy()
        # encoded_string_bytes = base64.b64encode(pix.tobytes())

        with tempfile.TemporaryFile() as temp_file:
            image.save(temp_file, format="PNG")

            temp_file.seek(0)
            encoded_string_bytes = base64.b64encode(temp_file.read())
            # The image is loaded into memory, but the file handle is closed
            # We need to create a copy to ensure it persists after the temp file is removed
            # image = Image.open(temp_file).copy()

        try:
            current_page = convert_page_to_markdown(
                f"data:image;base64,{encoded_string_bytes.decode('utf-8')}",
                # image
            )

            if last_page is not None:
                last_page, current_page = correct_page_overlap(last_page, current_page)
                yield (last_page, f"page_{page_counter}.md")

            last_page = current_page
            page_counter += 1
        except Exception as e:
            print(f"Error processing page {page_counter}: {str(e)}")
            # Skip this page and continue with the next one
            continue

    if last_page is not None:
        yield (last_page, f"page_{page_counter}.md")


def process_remote_document(job: ParseJob):
    with tempfile.TemporaryDirectory() as tempdir:
        # download source file
        source_file_path = os.path.join(tempdir, os.path.basename(job.source_file))

        download_file(job.source_file, source_file_path)
        page_contents = []

        # convert to markdown
        # upload each page to remote storage
        for page, title in convert_document(source_file_path):
            page_contents.append(page)
            print("page contents:", page)

            # TODO: post status updates

            # with open(os.path.join(tempdir, title), "w") as fp:
            #     print("page:", title)
            #     fp.write(page)
            #     upload_file(
            #         fp.name,
            #         os.path.join(
            #             "jobs",
            #             job.job_id,
            #             title,
            #         ),
            #     )

        # upload final document to remote storage
        final_document_path = os.path.join(tempdir, f"{job.job_id}.md")

        with open(final_document_path, "w") as fp:
            print("page contents:", page_contents)
            fp.write("\n".join(page_contents))
            # TODO: upload all docs + final doc as batch
            print("final document:", final_document_path)

        upload_file(
            final_document_path,
            os.path.join(
                "jobs",
                job.job_id,
                f"{job.job_id}.md",
            ),
        )


# async def convert_pdf_page_markdown(page: pymupdf.Page, semaphore: asyncio.Semaphore):
#     pix = page.get_pixmap()  # render page to an image
#     # pix.save(os.path.join(tempdir, "page-%i.png" % page.number))  # store image as a PNG
#     encoded_string = base64.b64encode(pix.tobytes())
#     # print(encoded_string)

#     prompt = """
#     Convert this image of a page from a PDF into markdown.
#     Convert the tables to valid markdown tables.
#     If there is an image or figure, replace it with an alternative text description.
#     Return the formatted markdown in a block starting with "<MARKDOWN>" and ending with "</MARKDOWN>"
#     """

#     async with semaphore:
#         timeout_sec = 1
#         retries_remaining = 5

#         while retries_remaining >= 0:
#             try:
#                 message = await client.messages.create(
#                     model="anthropic.claude-3-5-sonnet-20240620-v1:0",
#                     # model="anthropic.claude-3-haiku-20240307-v1:0",
#                     max_tokens=2048,
#                     messages=[
#                         {
#                             "role": "user",
#                             "content": [
#                                 {
#                                     "type": "image",
#                                     "source": {
#                                         "type": "base64",
#                                         "media_type": "image/png",
#                                         "data": encoded_string.decode("utf-8"),
#                                     },
#                                 },
#                                 {"type": "text", "text": prompt},
#                             ],
#                         }
#                     ],
#                 )

#                 content = message.content
#                 break
#             except RateLimitError as e:
#                 retries_remaining -= 1

#                 if retries_remaining <= 0:
#                     raise e
#                 else:
#                     print(
#                         f"Rate limit hit ({retries_remaining} tries remaining), retrying in {timeout_sec} seconds"
#                     )
#                     await asyncio.sleep(timeout_sec)

#                     timeout_sec *= random.randint(2, 4)
#                     continue

#     if content != [] and content[0].type == "text":
#         text = content[0].text
#         # print("before:", text)

#         sub1 = "<MARKDOWN>"
#         sub2 = "</MARKDOWN>"

#         idx1 = 0
#         idx2 = len(text)

#         try:
#             idx1 = text.index(sub1)
#         except ValueError:
#             pass

#         try:
#             idx2 = text.index(sub2)
#         except ValueError:
#             pass

#         # length of substring 1 is added to
#         # get string from next character
#         res = text[idx1 + len(sub1) + 1 : idx2]

#         print("after:", res)
#         return res
#     else:
#         return None


# async def convert_markdown(input_file_path: str, output_file_path: str):
#     doc = pymupdf.open(input_file_path)
#     sem = asyncio.Semaphore(1)

#     markdown_pages = await asyncio.gather(
#         *(convert_pdf_page_markdown(page, sem) for page in doc)
#     )

#     # TODO: can write directly to S3
#     with open(output_file_path, "w") as fp:
#         for page in markdown_pages:
#             fp.write(page)


# async def main():
#     # cds_files = s3fs.S3FileSystem(
#     #     endpoint_url=s3_url, key=s3_access_key_id, secret=s3_secret_access_key
#     # )

#     # cds_files.ls("llm-training-data-bucket/cds-files")
#     # TODO: download PDFs

#     with open("../../datasets.json", "r") as fp:
#         datasets = [CDSDataset(**doc) for doc in json.load(fp)["cds-files"]]

#     # await asyncio.gather(
#     #     *(
#     #         parse_and_save_document(
#     #             input_dir="../cds/pdf",
#     #             output_dir="../cds/md",
#     #             dataset=dataset,
#     #         )
#     #         for dataset in datasets
#     #         # if dataset.id in set(["arizona-state"])
#     #     )
#     # )
#     await asyncio.gather(
#         *(
#             convert_markdown(
#                 input_file_path=dataset.filename,
#                 output_file_path=os.path.join("../cds/md", f"{dataset.id}.md"),
#             )
#             for dataset in datasets
#             # if dataset.id in set(["arizona-state"])
#         )
#     )


# async def s3_transform_file(input_file: str, output_dir: str):
#     fs = s3fs.S3FileSystem()

#     with tempfile.TemporaryDirectory() as tempdir:
#         fs.get(input_file, tempdir)

#         input_path = os.path.join(tempdir, os.path.basename(input_file))
#         output_path = os.path.join(
#             tempdir, os.path.splitext(os.path.basename(input_file))[0] + ".md"
#         )

#         await convert_markdown(input_path, output_path)
#         fs.put(output_path, os.path.join(output_dir, os.path.basename(output_path)))
