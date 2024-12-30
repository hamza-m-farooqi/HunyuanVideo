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
    RUNPOD_POD_ID,
    RUNPOD_API_KEY,
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

# Global stop events for graceful thread control
stop_event = threading.Event()  # Application-wide shutdown
ack_extension_stop_event = threading.Event()  # For acknowledgment thread control

# Thread-safe lock for global variables
lock = threading.Lock()

last_message_acknowledge_time = time.time()
is_last_message_acknowledged = True

def check_idle_timeout():
    global last_message_acknowledge_time
    global is_last_message_acknowledged
    idle_timeout = 60  # Configurable idle timeout in seconds
    while not stop_event.is_set():
        try:
            with lock:
                if is_last_message_acknowledged:
                    current_time = time.time()
                    time_difference = None
                    if last_message_acknowledge_time:
                        time_difference = current_time - last_message_acknowledge_time
                    if time_difference and time_difference > idle_timeout:
                        print("Idle timeout reached. Stopping pod...")
                        import runpod

                        runpod.api_key = RUNPOD_API_KEY
                        runpod.stop_pod(RUNPOD_POD_ID)
                        break
                    else:
                        print(
                            f"Idle timeout not reached. Time difference: {time_difference}"
                        )
                else:
                    print("Message is being processed. Resetting idle timeout...")
        except Exception as e:
            print(f"Error during idle timeout check: {e}")
        time.sleep(5)

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

def acknowledge_message(message):
    global last_message_acknowledge_time
    global is_last_message_acknowledged
    with lock:
        last_message_acknowledge_time = time.time()
        is_last_message_acknowledged = True
    message.ack()
    print("Message acknowledged successfully!")

def callback(message):
    try:
        global is_last_message_acknowledged
        with lock:
            is_last_message_acknowledged = False
        print("message_id => ", message.message_id)
        message_data = message.data.decode("utf-8")
        parsed_message = json.loads(message_data)
        request_payload = None
        if "Field" in parsed_message:
            request_payload = json.loads(parsed_message["Field"])

        if not request_payload:
            print("No request payload found!")
            acknowledge_message(message)
            return
        print(f"Received message: {request_payload}")
        # Start a separate thread to keep extending the acknowledgment deadline during processing
        ack_extension_stop_event.clear()  # Ensure event is cleared before starting
        ack_extension_thread = threading.Thread(
            target=extend_ack_deadline, args=(message, ack_extension_stop_event)
        )
        ack_extension_thread.start()

        inference_request = InferenceRequest(**request_payload)
        inference_request.prompt = inference_request.prompt.replace(" ", "__")
        if inference_request.negative_prompt:
            inference_request.negative_prompt = (
                inference_request.negative_prompt.replace(" ", "_")
            )
        # Replace whitespace with underscores
        inference_job = InferenceJob(id=inference_request.id, request=inference_request)
        process_request(inference_job)

        acknowledge_message(message)
        print("Message acknowledged successfully!")

        # Stop the acknowledgment extension thread
        ack_extension_stop_event.set()
        ack_extension_thread.join()
        print("Exited Callback!")
    except Exception as e:
        print(f"Error processing message: {e}")
        acknowledge_message(message)

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

idle_time_checker_thread = threading.Thread(target=check_idle_timeout)
idle_time_checker_thread.start()

listen_for_messages()

while True:
    time.sleep(5)
