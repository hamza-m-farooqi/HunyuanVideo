import os
from decouple import config

# Get Base directory by getting the directory of current file and then its parent which will be directory of project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCLOUD_BUCKET_NAME = config("RUNPOD_SECRET_GCLOUD_STORAGE_BUCKET")
GCLOUD_CREDENTIALS = "gcloud-storage-key.json"
GCLOUD_PUB_SUB_CREDENTIALS = "gcloud-pubsub-key.json"
GCLOUD_PROJECT_ID = "soy-ascent-439610-b2"
GCLOUD_PUB_SUB_SUBSCRIPTION = config("RUNPOD_SECRET_GCLOUD_PUBSUB_SUBSCRIPTION")

RUN_POD_GCLOUD_STORAGE_KEY_ENV_VAR = "RUNPOD_SECRET_GCLOUD_STORAGE_KEY"
RUN_POD_GCLOUD_PUBSUB_KEY_ENV_VAR = "RUNPOD_SECRET_GCLOUD_PUBSUB_KEY"

RUNPOD_POD_ID = config("RUNPOD_POD_ID")
RUNPOD_API_KEY = config("RUNPOD_API_KEY")
print("RunPod Pod Id", RUNPOD_POD_ID)

RUNPOD_GPU_COUNT = config("RUNPOD_GPU_COUNT", default=4, cast=int)
RUNPOD_GPU_TYPE = config("RUNPOD_GPU_TYPE", default="NVIDIA_H100_80GB_HBM3")
