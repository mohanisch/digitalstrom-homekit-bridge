import json
import requests

from dsHomekit import config


def request(uri="", method="GET", payload=b''):
    request_data = None
    _base_uri = "api/v1"

    url = "https://{0}:{1}/{2}/apartment/{3}".format(
        config.args.hostname, config.args.http_port, _base_uri, uri)
    headers = {
        "Authorization": "Bearer %s" % config.args.token
    }
    if method == "GET":
        response = requests.get(
            url, headers=headers, verify=False
        )
        request_data = json.loads(response.content)['data']
    if method in ["PATCH"]:
        request_data = requests.patch(
            url, data=payload, headers=headers, verify=False
        )
    if method in ["POST"]:
        request_data = requests.post(
            url, data=payload, headers=headers, verify=False
        )
    return request_data
