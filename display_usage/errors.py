class HttpError(Exception):
    def __init__(self, code, url, body):
        super().__init__(f"HTTP {code}")
        self.code = code
        self.url = url
        self.body = body


class CredentialsMissing(Exception):
    pass


class WifiError(Exception):
    pass
