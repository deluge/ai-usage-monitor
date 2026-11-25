import json

from display_usage.errors import HttpError


def http_error(url, code, body="", headers=None):
    """Build an HttpError like ClaudeApi.request_json raises it."""
    return HttpError(code, url, body, headers)


class FakeResponse:
    def __init__(self, status_code, data=None, text="", headers=None):
        self.status_code = status_code
        self.text = json.dumps(data) if data is not None else text
        self.headers = headers or {}
        self.closed = False

    def json(self):
        return json.loads(self.text)

    def close(self):
        self.closed = True


class FakeRequest:
    def __init__(self, method, url, data, headers, timeout):
        self.method = method
        self.url = url
        self.data = data
        self.headers = headers
        self.timeout = timeout

    def json(self):
        return json.loads(self.data)


class FakeServer:
    """Replacement for requests.request.

    Answers each URL from its own queue: a dict is returned as JSON with status
    200, an int is returned as that status code with "error <code>" as body, a
    FakeResponse is returned as it is. Every request and response is recorded.
    """

    def __init__(self):
        self.responses = {}
        self.requests = []
        self.sent = []

    def add(self, url, *responses):
        self.responses.setdefault(url, []).extend(responses)

    def urls(self):
        return [request.url for request in self.requests]

    def __call__(self, method, url, data=None, headers=None, timeout=None):
        self.requests.append(FakeRequest(method, url, data, headers, timeout))
        response = self.responses[url].pop(0)
        if isinstance(response, int):
            response = FakeResponse(response, text=f"error {response}")
        elif isinstance(response, dict):
            response = FakeResponse(200, data=response)
        self.sent.append(response)
        return response


class FakeApi:
    """Replacement for ClaudeApi: returns or raises the given results in turn."""

    def __init__(self, *results, credentials_file="~/.usage-monitor/credentials.json"):
        self.results = list(results)
        self.credentials_file = credentials_file

    def fetch_usage(self):
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class FakeWifi:
    """Replacement for esp32.wifi.Wifi: connect() returns or raises the given results."""

    ssid = "Home"

    def __init__(self, *results):
        self.results = list(results)

    def connect(self):
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result
