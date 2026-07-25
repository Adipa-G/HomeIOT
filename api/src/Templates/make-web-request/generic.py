try:
    import urequests as requests
except ImportError:  # pragma: no cover - desktop fallback
    import requests

# Change this to the endpoint you want to poll.
URL = "https://example.com/api/status"


def run(ctx):
    response = requests.get(URL)
    status_code = response.status_code
    body = response.text
    response.close()
    return {
        "url": URL,
        "status_code": status_code,
        "body": body,
    }
