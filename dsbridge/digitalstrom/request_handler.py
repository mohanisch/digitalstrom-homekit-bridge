import requests
import urllib3

from metrics import REQUEST_TIME, request_counter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RequestHandler:
    def __init__(self, base_url, token, **kwargs):
        self.token = token
        self.base_url = base_url
        self.session = requests.Session()
        self.headers = {"Authorization": f"Bearer {self.token}"}

        for arg in kwargs:
            if isinstance(kwargs[arg], dict):
                kwargs[arg] = self.__deep_merge(getattr(self.session, arg), kwargs[arg])
            setattr(self.session, arg, kwargs[arg])

    @REQUEST_TIME.time()
    def get(self, url, **kwargs):

        request = self.session.get(
            self.base_url + url,
            headers=self.headers,
            verify=False,
            **kwargs
        )
        request_counter.labels(status_code=request.status_code).inc()

        return request.json()

    @REQUEST_TIME.time()
    def post(self, url, **kwargs):
        request = self.session.post(
            self.base_url + url,
            headers=self.headers,
            verify=False,
            **kwargs
        )
        request_counter.labels(status_code=request.status_code).inc()

        return request

    @REQUEST_TIME.time()
    def patch(self, url, **kwargs):
        request = self.session.patch(
            self.base_url + url,
            headers=self.headers,
            verify=False,
            **kwargs
        )
        request_counter.labels(status_code=request.status_code).inc()

        return request

    @REQUEST_TIME.time()
    def get_token(self, api):
        param = {"loginToken": f"{self.token}"}
        request = self.session.get(
            self.base_url + api + "/loginApplication",
            headers=self.headers,
            verify=False,
            params=param
        )
        request_counter.labels(status_code=request.status_code).inc()

        return request.json()['result']['token']

    @staticmethod
    def __deep_merge(source, destination):
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                RequestHandler.__deep_merge(value, node)
            else:
                destination[key] = value
        return destination
