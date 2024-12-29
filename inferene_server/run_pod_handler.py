"""
Contains the handler function that will be called by the serverless.
"""

import json
import torch

print("Going to access files from server")
from run_pod_schema import INPUT_SCHEMA
from request_params import (
    InferenceRequest,
    InferenceJob,
)
from request_processor import process_request
from server_utils import save_gcloud_storage_key

print("Going to access files from runpod")
import runpod
from runpod.serverless.utils.rp_validator import validate

torch.cuda.empty_cache()

save_gcloud_storage_key()


@torch.inference_mode()
def generate_video(job):
    """
    Generate an image from text using your Model
    """
    job_input = job["input"]

    # Input validation
    validated_input = validate(job_input, INPUT_SCHEMA)

    if "errors" in validated_input:
        return {"error": validated_input["errors"]}
    job_input = validated_input["validated_input"]
    inferene_request = InferenceRequest(**job_input)
    inferene_request.prompt = inferene_request.prompt.replace(" ", "__")
    if inferene_request.negative_prompt:
        inferene_request.negative_prompt = inferene_request.negative_prompt.replace(
            " ", "_"
        )
    # replace whitespace with underscore
    inference_job = InferenceJob(id=inferene_request.id, request=inferene_request)
    process_request(inference_job)
    return json.loads(inference_job.json())


runpod.serverless.start({"handler": generate_video})
