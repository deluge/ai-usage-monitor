import email.message
import io
import json
import urllib.error


def http_error(url, code, body="", headers=None):
    """Build an HTTPError like urllib raises it, with a readable body."""
    message = email.message.Message()
    for name, value in (headers or {}).items():
        message[name] = value
    return urllib.error.HTTPError(url, code, f"HTTP {code}", message, io.BytesIO(body.encode()))


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


class FakeServer:
    """Replacement for urllib.request.urlopen.

    Answers each URL from its own queue: a dict is returned as JSON, an int is
    raised as an HTTPError with that status code. Every request is recorded.
    """

    def __init__(self):
        self.responses = {}
        self.requests = []

    def add(self, url, *responses):
        self.responses.setdefault(url, []).extend(responses)

    def urls(self):
        return [request.full_url for request in self.requests]

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        response = self.responses[request.full_url].pop(0)
        if isinstance(response, int):
            raise http_error(request.full_url, response, body=f"error {response}")
        return FakeResponse(json.dumps(response).encode())


class FakeApi:
    """Replacement for ClaudeApi: returns or raises the given results in turn."""

    def __init__(self, *results, credentials_file="/home/pi/.usage-monitor/credentials.json"):
        self.results = list(results)
        self.credentials_file = credentials_file

    def fetch_usage(self):
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result
