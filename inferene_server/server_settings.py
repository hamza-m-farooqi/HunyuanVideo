import os
from decouple import config

# Get Base directory by getting the directory of current file and then its parent which will be directory of project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCLOUD_BUCKET_NAME = config("RUNPOD_SECRET_GCLOUD_STORAGE_BUCKET")
GCLOUD_CREDENTIALS = "gcloud-storage-key.json"
