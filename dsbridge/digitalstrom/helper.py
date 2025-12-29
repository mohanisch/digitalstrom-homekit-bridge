import uuid

from ..config import args


def generate_dsuid(name: str) -> str:
    _uuid = uuid.uuid3(uuid.NAMESPACE_OID, name)
    return str(_uuid).replace("-", "") + '00'


def create_application_token(password):
    """Create application token for digitalStrom API with error handling."""
    import logging
    import os

    import requests
    import urllib3
    from ..digitalstrom import SYSTEM_API

    logger = logging.getLogger(__name__)

    # Determine SSL verification setting
    env_verify = os.environ.get('DSS_VERIFY_SSL', 'true').lower()
    verify_ssl = env_verify in ('true', '1', 'yes', 'on')

    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning(
            "SSL certificate verification is DISABLED. This is insecure and should only be used "
            "for testing or with self-signed certificates in trusted networks."
        )

    session = requests.Session()
    host = args.dss_hostname + ":" + args.dss_http_port
    base_url = "https://" + host + "/" + SYSTEM_API

    try:
        # Step 1: Login
        logintoken_param = {"user": "dssadmin", "password": password}
        logintoken_response = session.get(
            base_url + '/login',
            params=logintoken_param,
            verify=verify_ssl,
            timeout=10
        )
        logintoken_response.raise_for_status()
        logintoken = logintoken_response.json()

        if not logintoken.get('ok'):
            logger.error("Login failed: %s", logintoken.get('message', 'Unknown error'))
            return logintoken

        # Step 2: Request application token
        application_token_param = {"applicationName": "dS HomeKit bridge"}
        application_token_response = requests.get(
            base_url + '/requestApplicationToken',
            params=application_token_param,
            verify=verify_ssl,
            timeout=10
        )
        application_token_response.raise_for_status()
        application_token = application_token_response.json()

        # Step 3: Enable token
        param = {"applicationToken": application_token['result']['applicationToken']}
        headers = {"Cookie": "token=%s" % logintoken['result']['token']}
        enable_token_response = requests.get(
            base_url + '/enableToken',
            headers=headers,
            params=param,
            verify=verify_ssl,
            timeout=10
        )
        enable_token_response.raise_for_status()
        enable_application_token = enable_token_response.json()

        # Add token to result
        enable_application_token['token'] = application_token['result']['applicationToken']
        logger.info("Successfully created application token")

        return enable_application_token

    except requests.exceptions.SSLError as e:
        import ssl
        if isinstance(e.args[0], ssl.SSLError) and 'CERTIFICATE_VERIFY_FAILED' in str(e):
            logger.error(
                "SSL certificate verification failed. "
                "This usually happens with self-signed certificates. "
                "To disable SSL verification, set environment variable: DSS_VERIFY_SSL=false"
            )
        logger.error("SSL error creating application token: %s", e, exc_info=True)
        return {
            'ok': False,
            'message': f"SSL error: {str(e)}. Set DSS_VERIFY_SSL=false to disable verification."
        }
    except requests.exceptions.RequestException as e:
        logger.error("Error creating application token: %s", e, exc_info=True)
        return {
            'ok': False,
            'message': f"Request failed: {str(e)}"
        }
    except KeyError as e:
        logger.error("Unexpected response structure: %s", e, exc_info=True)
        return {
            'ok': False,
            'message': f"Unexpected response format: {str(e)}"
        }
    except Exception as e:
        logger.error("Unexpected error creating token: %s", e, exc_info=True)
        return {
            'ok': False,
            'message': f"Unexpected error: {str(e)}"
        }
