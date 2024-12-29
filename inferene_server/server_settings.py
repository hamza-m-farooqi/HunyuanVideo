import os
from decouple import config

# Get Base directory by getting the directory of current file and then its parent which will be directory of project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCLOUD_BUCKET_NAME = config("GCLOUD_BUCKET_NAME")
GCLOUD_CREDENTIALS = config("GCLOUD_CREDENTIALS")
