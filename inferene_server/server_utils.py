import requests
from threading import Thread


def webhook_response(training_webhook_url, data=None):
    def send(training_webhook_url, data=None):
        if training_webhook_url and "http" in training_webhook_url:
            requests.post(training_webhook_url, json=data)

    Thread(target=send, args=(training_webhook_url, data)).start()
    return None
