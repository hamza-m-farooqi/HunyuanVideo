import os
import re
import pytz
import json
import select
import subprocess
import server_settings as server_settings
from request_params import (
    InferenceModel,
    InferenceJob,
    InferenceResponse,
    InferenceStatus,
)
from server_utils import webhook_response
from gcloud_utils import upload as upload_to_gcloud
from datetime import datetime
from runpod.serverless.utils import rp_cleanup


def background_inference(job: InferenceJob):
    try:
        save_path = os.path.join(server_settings.BASE_DIR, job.id)
        job.gpu_count = server_settings.RUNPOD_GPU_COUNT
        job.gpu_type = server_settings.RUNPOD_GPU_TYPE
        command = None
        if job.request.model == InferenceModel.YOTTA_VIDEO_FP16:
            command = f"bash -c 'torchrun --nproc_per_node=4 /home/HunyuanVideo/sample_video.py --prompt {job.request.prompt} --video-size {job.request.height} {job.request.width} --video-length {job.request.video_length} --seed {job.request.seed} --neg-prompt {job.request.negative_prompt} --infer-steps {job.request.infer_steps} --cfg-scale {job.request.guidance_scale} --flow-shift {job.request.flow_shift} --num-videos {job.request.num_videos_per_prompt} --ulysses-degree {job.request.ulysses_degree} --ring-degree {job.request.ring_degree} --save-path {save_path} --flow-reverse'"
        elif job.request.model == InferenceModel.YOTTA_VIDEO_FP8 and job.gpu_count == 1:
            dit_weight_path = os.path.join(
                server_settings.BASE_DIR,
                "ckpts",
                "hunyuan-video-t2v-720",
                "transformers",
                "mp_rank_00_model_states_fp8.pt",
            )
            dit_weight_path="/home/HunyuanVideo/ckpts/hunyuan-video-t2v-720p/transformers/mp_rank_00_model_states_fp8.pt"
            print("DIT WEIGHT PATH",dit_weight_path)
            command = f"bash -c 'python3 /home/HunyuanVideo/sample_video.py --dit-weight {dit_weight_path} --prompt {job.request.prompt} --video-size {job.request.height} {job.request.width} --video-length {job.request.video_length} --seed {job.request.seed} --neg-prompt {job.request.negative_prompt} --infer-steps {job.request.infer_steps} --cfg-scale {job.request.guidance_scale} --flow-shift {job.request.flow_shift} --num-videos {job.request.num_videos_per_prompt} --save-path {save_path} --use-fp8 --embedded-cfg-scale 6.0'"
        elif job.request.model == InferenceModel.YOTTA_VIDEO_FP8 and job.gpu_count == 4:
            dit_weight_path = os.path.join(
                server_settings.BASE_DIR,
                "ckpts",
                "hunyuan-video-t2v-720",
                "transformers",
                "mp_rank_00_model_states_fp8.pt",
            )
            print(dit_weight_path)
            command = f"bash -c 'torchrun --nproc_per_node=4 /home/HunyuanVideo/sample_video.py --dit-weight {dit_weight_path} --prompt {job.request.prompt} --video-size {job.request.height} {job.request.width} --video-length {job.request.video_length} --seed {job.request.seed} --neg-prompt {job.request.negative_prompt} --infer-steps {job.request.infer_steps} --cfg-scale {job.request.guidance_scale} --flow-shift {job.request.flow_shift} --num-videos {job.request.num_videos_per_prompt} --ulysses-degree {job.request.ulysses_degree} --ring-degree {job.request.ring_degree} --save-path {save_path} --use-fp8 --embedded-cfg-scale 6.0'"
        else:
            job.status = InferenceStatus.FAILED.value
            job.message = "Invalid GPU count"
            webhook_response(job.request.webhook_url, json.loads(job.json()))
            return
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
            job.end_time = datetime.now(pytz.utc)
            webhook_response(job.request.webhook_url, json.loads(job.json()))

        except subprocess.CalledProcessError as e:
            print(e)
            job.status = InferenceStatus.FAILED.value
            job.message = str(e)
            webhook_response(job.request.webhook_url, json.loads(job.json()))
            raise Exception(str(e))

        except Exception as e:
            print(e)
            job.status = InferenceStatus.FAILED.value
            job.message = str(e)
            webhook_response(job.request.webhook_url, json.loads(job.json()))
            raise Exception(str(e))
    except Exception as e:
        print(e)
        job.status = InferenceStatus.FAILED.value
        job.message = str(e)
        webhook_response(job.request.webhook_url, json.loads(job.json()))
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
