import base64
import tempfile
import os
import io

# from anthropic import AsyncAnthropicBedrock, RateLimitError
import fitz
from PIL import Image

# import s3fs

from worker import clients, config
from worker.model import get_model, get_processor
from worker.types import ParseJob


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


def download_file(source: str, destination: str):
    with open(destination, "wb+") as fp:
        res = clients.supabase.storage.from_(
            config.SUPABASE_UPLOADS_BUCKET,
        ).download(source)
        fp.write(res)


def upload_file(source: str, destination: str):
    with open(source, "rb") as fp:
        clients.supabase.storage.from_(
            config.SUPABASE_JOBS_BUCKET,
        ).upload(destination, fp)


def convert_page_to_markdown(image: Image.Image):
    return process_vision_info(
        [
            {
                "role": "user",
                "content": "Convert this image of a page from a PDF into markdown.",
            }
        ],
        [image],
    )


def correct_page_overlap(last_page: str, current_page: str):
    # last_page = ""
    # current_page = ""

    return last_page, current_page


def convert_document(input_file_path: str):
    doc = fitz.open(input_file_path)
    last_page = None
    page_counter = 0

    for page in doc:
        pix = page.get_pixmap()  # type: ignore

        image = Image.open(io.BytesIO(pix.tobytes()))
        # print("width:", image.width)
        # print("height:", image.height)

        # image.resize((width, height))
        new_width = min(((image.width + 27) // 28) * 28, 16384)
        new_height = min(((image.height + 27) // 28) * 28, 16384)

        image.resize((new_width, new_height))
        # encoded_string_bytes = base64.b64encode(pix.tobytes())

        current_page = convert_page_to_markdown(
            # encoded_string_bytes.decode("utf-8"),
            image
        )

        if last_page is not None:
            last_page, current_page = correct_page_overlap(last_page, current_page)
            yield (last_page, f"page_{page_counter}.md")

        last_page = current_page
        page_counter += 1

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
