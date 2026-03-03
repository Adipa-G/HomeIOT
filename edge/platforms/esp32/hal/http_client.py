from edge.shared.hal.interfaces import IHttpClient, HttpResponse


class MicroPythonHttpClient(IHttpClient):
    def get(self, url, headers=None):
        try:
            import urequests as requests
        except ImportError:  # pragma: no cover - desktop fallback
            import requests

        response = requests.get(url, headers=headers)
        text = response.text if hasattr(response, "text") else ""
        content = response.content if hasattr(response, "content") else b""
        status_code = response.status_code
        if hasattr(response, "close"):
            response.close()
        return HttpResponse(status_code=status_code, text=text, content=content)

    def post(self, url, data, headers=None):
        try:
            import urequests as requests
        except ImportError:  # pragma: no cover - desktop fallback
            import requests

        response = requests.post(url, json=data, headers=headers)
        text = response.text if hasattr(response, "text") else ""
        content = response.content if hasattr(response, "content") else b""
        status_code = response.status_code
        if hasattr(response, "close"):
            response.close()
        return HttpResponse(status_code=status_code, text=text, content=content)
