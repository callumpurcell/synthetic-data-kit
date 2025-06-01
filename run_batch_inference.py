#!/usr/bin/env python3
import os
import time
import json
import argparse

from mistralai import Mistral


def parse_args():
    parser = argparse.ArgumentParser(
        description="Upload a JSONL of batch requests to Mistral, run the job, poll until completion, "
                    "and download the raw JSONL results."
    )
    parser.add_argument(
        "--batch_file",
        required=True,
        help="Path to the JSONL file containing batch requests (one JSON object per line)."
    )
    parser.add_argument(
        "--output_dir",
        required=True,
        help="Directory where the batch results JSONL will be saved."
    )
    parser.add_argument(
        "--poll_interval",
        type=int,
        default=5,
        help="Seconds to wait between polling job status (default: 5)."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    batch_path = args.batch_file
    out_dir = args.output_dir
    poll_interval = args.poll_interval

    if not os.path.isfile(batch_path):
        raise FileNotFoundError(f"Batch file not found: {batch_path}")

    os.makedirs(out_dir, exist_ok=True)

    # 1. Initialize Mistral client using environment variable
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise EnvironmentError("Please set the MISTRAL_API_KEY environment variable.")
    client = Mistral(api_key=api_key)

    # 2. Upload the JSONL file with purpose="batch" (so Mistral treats it as batch‐inference data)
    print(f"Uploading batch file {batch_path} to Mistral (purpose='batch')...")
    with open(batch_path, "rb") as f_in:
        upload_resp = client.files.upload(
            file={
                "file_name": os.path.basename(batch_path),
                "content": f_in
            },
            purpose="batch"    # ← this line is required for batch inference :contentReference[oaicite:0]{index=0}
        )
    batch_file_id = upload_resp.id
    print(f"Uploaded → file_id = {batch_file_id}")

    # 3. Create a batch job pointing to that file
    print("Creating batch job...")
    batch_resp = client.batch.jobs.create(
        input_files=[batch_file_id],
        endpoint="/v1/chat/completions",
        model="mistral-small-2409"
    )
    job_id = batch_resp.id
    print(f"Batch job created → job_id = {job_id}")

    # 4. Poll the job until it’s done (status == "succeeded" or "failed")
    print("Polling job status...", end="", flush=True)
    while True:
        status_resp = client.batch.jobs.get(job_id=job_id)
        status = status_resp.status
        print(f"\n  • status = {status}")
        if status in ("succeeded", "failed"):
            break
        time.sleep(poll_interval)

    if status != "succeeded":
        print(f"❌ Batch job failed. Errors: {status_resp.errors}")
        return

    print("✅ Batch job succeeded!")

    # 5. Download the output JSONL file
    output_file_id = status_resp.output_file
    print(f"Retrieving output file (id={output_file_id})...")
    output_stream = client.files.retrieve(id=output_file_id)

    raw_bytes = output_stream.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = raw_bytes.decode("utf-8", errors="ignore")

    # 6. Write the raw JSONL lines to disk
    results_path = os.path.join(out_dir, "batch_results.jsonl")
    with open(results_path, "w", encoding="utf-8") as fout:
        fout.write(raw_text)

    print(f"Raw batch results written to: {results_path}")


if __name__ == "__main__":
    main()
