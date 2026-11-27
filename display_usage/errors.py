class HttpError(Exception):
    def __init__(self, code, url, body, headers=None):
        super().__init__(f"HTTP {code}")
        self.code = code
        self.url = url
        self.body = body
        # Header names are lowercased: servers and the requests libraries of
        # CPython and MicroPython don't agree on their case.
        self.headers = {name.lower(): value for name, value in (headers or {}).items()}


class CredentialsMissing(Exception):
    pass


class WifiError(Exception):
    pass


class SettingsError(Exception):
    pass
