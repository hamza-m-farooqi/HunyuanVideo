"""
Contains the handler function that will be called by the serverless.
"""

import sys
import json
import time
import torch
import signal
import threading
from request_params import (
    InferenceRequest,
    InferenceJob,
)
from server_settings import (
    GCLOUD_PUB_SUB_CREDENTIALS,
    GCLOUD_PROJECT_ID,
    GCLOUD_PUB_SUB_SUBSCRIPTION,
    RUN_POD_GCLOUD_STORAGE_KEY_ENV_VAR,
    RUN_POD_GCLOUD_PUBSUB_KEY_ENV_VAR,
    GCLOUD_CREDENTIALS,
    GCLOUD_PUB_SUB_CREDENTIALS,
)
from request_processor import process_request
from server_utils import save_gcloud_keys
from google.oauth2 import service_account
from google.cloud import pubsub_v1


save_gcloud_keys(RUN_POD_GCLOUD_STORAGE_KEY_ENV_VAR, GCLOUD_CREDENTIALS)
save_gcloud_keys(RUN_POD_GCLOUD_PUBSUB_KEY_ENV_VAR, GCLOUD_PUB_SUB_CREDENTIALS)
credentials = service_account.Credentials.from_service_account_file(
    GCLOUD_PUB_SUB_CREDENTIALS
)

subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
subscription_path = subscriber.subscription_path(
    GCLOUD_PROJECT_ID, GCLOUD_PUB_SUB_SUBSCRIPTION
)

torch.cuda.empty_cache()

# Global stop event to handle graceful shutdown
stop_event = threading.Event()


def extend_ack_deadline(message, stop_event, interval=30):
    while not stop_event.is_set():
        try:
            print(
                f"Extending acknowledgment deadline for message: {message.message_id}"
            )
            message.modify_ack_deadline(60)  # Extend the deadline by 60 seconds
            time.sleep(interval)  # Modify the deadline every 30 seconds
        except Exception as e:
            print(f"Error extending acknowledgment deadline: {e}")
            break


def callback(message):
    try:
        # Decode and load the JSON message
        print("message_id => ", message.message_id)
        message_data = message.data.decode("utf-8")
        parsed_message = json.loads(message_data)
        request_payload = None
        if "Field" in parsed_message:
            request_payload = json.loads(parsed_message["Field"])

        if not request_payload:
            print("No request payload found!")
            message.ack()
            return
        print(f"Received message: {request_payload}")
        # Start a separate thread to keep extending the acknowledgment deadline during processing
        ack_extension_thread = threading.Thread(
            target=extend_ack_deadline, args=(message, stop_event)
        )
        ack_extension_thread.start()

        inferene_request = InferenceRequest(**request_payload)
        inferene_request.prompt = inferene_request.prompt.replace(" ", "__")
        if inferene_request.negative_prompt:
            inferene_request.negative_prompt = inferene_request.negative_prompt.replace(
                " ", "_"
            )
        # replace whitespace with underscore
        inference_job = InferenceJob(id=inferene_request.id, request=inferene_request)
        process_request(inference_job)

        message.ack()
        print("Message acknowledged successfully!")

        # Stop the acknowledgment extension thread
        stop_event.set()
        ack_extension_thread.join()
        print("Exited Callback!")
    except Exception as e:
        print(f"Error processing message: {e}")
        message.ack()


def listen_for_messages():
    # Flow control settings: only allow 1 message at a time
    flow_control = pubsub_v1.types.FlowControl(
        max_messages=1,  # Limit the number of messages being pulled concurrently
        max_bytes=10 * 1024 * 1024,  # Optionally limit the total message size
    )

    # Subscribe and listen for messages
    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=callback,
        flow_control=flow_control,
    )
    print(f"Listening for messages on {subscription_path}...")

    try:
        streaming_pull_future.result()  # Keeps the listener active
    except KeyboardInterrupt:
        print("Interrupt received, cancelling the subscription...")
        streaming_pull_future.cancel()
        stop_event.set()  # Set the global stop event to stop any ongoing threads


def handle_termination_signal(signum, frame):
    print("Received termination signal. Stopping listener...")
    stop_event.set()
    sys.exit(0)


# Register the signal handlers to gracefully stop the application
signal.signal(signal.SIGTERM, handle_termination_signal)
signal.signal(signal.SIGINT, handle_termination_signal)

listen_for_messages()
while True:
    time.sleep(5)
