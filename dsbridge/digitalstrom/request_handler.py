from .const import SYSTEM_API

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DsRequest:
    def __init__(self, base_url, token, **kwargs):
        self.token = token
        self.base_url = base_url
        self.session = requests.Session()
        self.headers = {"Authorization": "Bearer %s" % self.token}

        for arg in kwargs:
            if isinstance(kwargs[arg], dict):
                kwargs[arg] = self.__deep_merge(getattr(self.session, arg), kwargs[arg])
            setattr(self.session, arg, kwargs[arg])

    def get(self, url, **kwargs):
        return self.session.get(
            self.base_url + url,
            headers=self.headers,
            verify=False,
            **kwargs
        ).json()

    def post(self, url, **kwargs):
        return self.session.post(
            self.base_url + url,
            headers=self.headers,
            verify=False,
            **kwargs
        )

    def patch(self, url, **kwargs):
        return self.session.patch(
            self.base_url + url,
            headers=self.headers,
            verify=False,
            **kwargs
        )

    def get_token(self):
        param = {"loginToken": "%s" % self.token}

        return self.session.get(
            self.base_url + SYSTEM_API + "/loginApplication",
            headers=self.headers,
            verify=False,
            params=param
        ).json()['result']['token']

    @staticmethod
    def __deep_merge(source, destination):
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                DsRequest.__deep_merge(value, node)
            else:
                destination[key] = value
        return destination
