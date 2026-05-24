"""Basic example: process a single document and export as JSONL."""
import os
from flexorch_sdk import FlexOrchClient

client = FlexOrchClient(os.environ["FLEXORCH_API_KEY"])

job = client.process("contract.pdf", locale="tr").wait()

print(f"Quality grade : {job.quality_grade}")
print(f"Quality score : {job.quality_score}")

dataset = job.dataset()
if dataset:
    dataset.export("jsonl", path="output.jsonl")
    print(f"Exported {dataset.row_count} rows → output.jsonl")
