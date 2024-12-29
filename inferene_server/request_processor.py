import os
import re
import json
import select
import subprocess
import uuid
import requests
from threading import Thread
from PIL import Image
import server_settings as server_settings
from request_params import (
    InferenceJob,
    InferenceResponse,
    InferenceStatus,
)
from server_utils import webhook_response
from gcloud_utils import upload as upload_to_gcloud
from runpod.serverless.utils import rp_cleanup


def background_inference(job: InferenceJob):
    save_path = os.path.join(server_settings.BASE_DIR, job.id)
    command = f"bash -c 'torchrun --nproc_per_node=4 sample_video.py --video-size {job.request.height} {job.request.width} --video-length {job.request.video_length} --infer-steps {job.request.infer_steps} --prompt {job.request.prompt} --flow-reverse --seed {job.request.seed} --ulysses-degree {job.request.ulysses_degree}  --ring-degree {job.request.ring_degree} --save-path {save_path}'"
    webhook_response(job.request.webhook_url, json.loads(job.json()))
    print(command)

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Use select to read from stdout and stderr without blocking
        inferene_progress = None
        stderr_output = []
        while True:
            reads = [process.stdout.fileno(), process.stderr.fileno()]
            ret = select.select(reads, [], [])
            for fd in ret[0]:
                if fd == process.stdout.fileno():
                    read = process.stdout.readline()
                    if read:
                        output = read.strip()
                        print(output)
                        percentage = 0
                        if f"/{job.request.infer_steps}" in output:
                            percentage_value = get_progress_percentage(output)
                            percentage = percentage_value if percentage_value else 0

                        job.progress = percentage
                        if inferene_progress is None or job.progress >= (
                            inferene_progress + 5
                        ):
                            inferene_progress = job.progress
                            webhook_response(
                                job.request.webhook_url,
                                json.loads(job.json()),
                            )
                if fd == process.stderr.fileno():
                    read = process.stderr.readline()
                    if read:
                        output = read.strip()
                        print(output)
                        stderr_output.append(output)
                        percentage = 0
                        if f"/{job.request.infer_steps}" in output:
                            percentage_value = get_progress_percentage(output)
                            percentage = percentage_value if percentage_value else 0
                        job.progress = percentage
                        if inferene_progress is None or job.progress >= (
                            inferene_progress + 5
                        ):
                            inferene_progress = job.progress
                            webhook_response(
                                job.request.webhook_url,
                                json.loads(job.json()),
                            )
                print(job.progress)
            if process.poll() is not None:
                break

        return_code = process.poll()
        if return_code != 0:
            stderr_combined = "\n".join(stderr_output)
            raise subprocess.CalledProcessError(
                return_code, command, output=stderr_combined
            )

        print("Job is Finished")
        process_response(job, save_path)
        job.progress = 100
        job.status = InferenceStatus.COMPLETED.value
        webhook_response(job.request.webhook_url, json.loads(job.json()))

    except subprocess.CalledProcessError as e:
        print(e)
        job.status = InferenceStatus.FAILED.value
        job.message = str(e)
        raise Exception(str(e))

    except Exception as e:
        print(e)
        job.status = InferenceStatus.FAILED.value
        job.message = str(e)
        raise Exception(str(e))


def process_request(job: InferenceJob):
    job.status = InferenceStatus.PROCESSING.value
    job.message = "Job Started"
    webhook_response(
        job.request.webhook_url,
        json.loads(job.json()),
    )
    background_inference(job)


def get_progress_percentage(output_line):
    # Regex pattern to find the diffusion process progress
    pattern = re.compile(r"(\d+)/(\d+)\s+\[")
    match = pattern.search(output_line)
    if match:
        current, total = map(int, match.groups())
        percentage = (current / total) * 100
        return percentage
    return None


def process_response(job: InferenceJob, save_path: str):
    output_videos = (
        {f for f in os.listdir(save_path) if f.endswith(".mp4")}
        if os.path.exists(save_path)
        else set()
    )
    if output_videos:
        for video_file in output_videos:
            print(f"Video file found: {video_file}")
            video_path = os.path.join(save_path, video_file)
            video_url = upload_to_gcloud(video_path, job.cloud_storage_folder)
            inference_response = InferenceResponse(video_url=video_url)
            job.results.append(inference_response)
        rp_cleanup.clean([save_path])
