import pytz
from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel


class InferenceRequest(BaseModel):
    id: str
    prompt: str
    height: int
    width: int
    video_length: int
    seed: int
    negative_prompt: str | None = None
    infer_steps: int
    guidance_scale: float
    flow_shift: float
    num_videos_per_prompt: int
    ulysses_degree: int
    ring_degree: int
    webhook_url: str


class InferenceStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InferenceResponse(BaseModel):
    video_url: str


class InferenceJob(BaseModel):
    id: str = None
    request: InferenceRequest = None
    progress: int = 0
    status: str = InferenceStatus.PENDING.value  # Initial status
    results: List[InferenceResponse] = []
    cloud_storage_folder: str = None
    start_time: datetime = None
    end_time: datetime = None
    message: str = None

    def __init__(self, **data):
        super().__init__(**data)
        # Dynamically set job_s3_folder using job_id and current date
        if self.id:
            self.cloud_storage_folder = (
                f"hunyuan-videos/{datetime.now().strftime('%Y-%m-%d')}/{self.id}/"
            )
        # set utc start time when job is created
        self.start_time = datetime.now(pytz.utc)
