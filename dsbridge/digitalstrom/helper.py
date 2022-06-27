import uuid

from ..config import args


def generate_dsuid(name: str) -> str:
    _uuid = uuid.uuid3(uuid.NAMESPACE_OID, name)
    return str(_uuid).replace("-", "") + '00'


def create_application_token(password):
    import requests
    import urllib3
    from homekit.digitalstrom import SYSTEM_API
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    result = {}
    session = requests.Session()

    host = args.hostname + ":" + args.http_port

    logintoken_param = {"user": "dssadmin", "password": password}
    logintoken = session.get("https://" + host + "/" + SYSTEM_API + '/login', params=logintoken_param,
                             verify=False).json()

    if logintoken['ok']:
        application_token_param = {"applicationName": "dS HomeKit bridge"}
        application_token = requests.get(
            "https://" + host + "/" + SYSTEM_API + '/requestApplicationToken',
            params=application_token_param,
            verify=False
        ).json()

        param = {"applicationToken": application_token['result']['applicationToken']}
        headers = {"Cookie": "token=%s" % logintoken['result']['token']}
        enable_application_token = requests.get(
            "https://" + host + "/" + SYSTEM_API + '/enableToken',
            headers=headers,
            params=param,
            verify=False
        ).json()
        enable_application_token['token'] = application_token['result']['applicationToken']
        result = enable_application_token

    else:
        result = logintoken

    return result
