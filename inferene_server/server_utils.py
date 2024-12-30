import os
import json
import requests
from threading import Thread
from server_settings import BASE_DIR

def webhook_response(training_webhook_url, data=None):
    print("Going to send webhook response",training_webhook_url)
    def send(training_webhook_url, data=None):
        if training_webhook_url and "http" in training_webhook_url:
            requests.post(training_webhook_url, json=data)
            print("Webhook response sent",training_webhook_url)
    Thread(target=send, args=(training_webhook_url, data)).start()
    return None


def is_json_compatible(value):
    try:
        json.loads(value)
        return True
    except (TypeError, ValueError):
        return False


def save_gcloud_keys(env_var_name: str, file_name: str):
    file_name = os.path.join(BASE_DIR, file_name)
    if os.path.exists(file_name):
        print(f"The file {file_name} already exists.")
        return
    env_var_name = env_var_name
    env_var_value = os.getenv(env_var_name)
    if is_json_compatible(env_var_value):
        try:
            with open(file_name, "w") as json_file:
                json.dump(json.loads(env_var_value), json_file, indent=4)
            print(f"The JSON-compatible value was successfully saved to {file_name}.")
        except Exception as e:
            print(f"Error saving to file: {e}")
