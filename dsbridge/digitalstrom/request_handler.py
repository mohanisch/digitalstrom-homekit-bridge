import logging
import os
import ssl
import time
from functools import wraps
from typing import Optional, Dict, Any

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dsbridge.metrics import REQUEST_TIME, request_counter

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 2, backoff_factor: float = 0.2):  # Reduced for faster response on Pi
    """
    Decorator for retrying failed requests with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff delay
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except (requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                        requests.exceptions.RequestException) as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = backoff_factor * (2 ** attempt)
                        logger.warning(
                            "Request failed (attempt %d/%d): %s. Retrying in %.2f seconds...",
                            attempt + 1,
                            max_retries + 1,
                            str(e),
                            delay
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "Request failed after %d attempts: %s",
                            max_retries + 1,
                            str(e),
                            exc_info=True
                        )
                except requests.exceptions.HTTPError as e:
                    # Don't retry on HTTP errors (4xx, 5xx) unless it's a server error
                    if e.response.status_code >= 500 and attempt < max_retries:
                        delay = backoff_factor * (2 ** attempt)
                        logger.warning(
                            "Server error %d (attempt %d/%d). Retrying in %.2f seconds...",
                            e.response.status_code,
                            attempt + 1,
                            max_retries + 1,
                            delay
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise

            # If we get here, all retries failed
            raise last_exception

        return wrapper

    return decorator


class RequestHandler:
    """
    HTTP request handler with connection pooling, retry logic, and configurable SSL verification.
    """

    def __init__(self, base_url: str, token: str, verify_ssl: Optional[bool] = None, **kwargs):
        """
        Initialize RequestHandler.
        
        Args:
            base_url: Base URL for API requests
            token: Authentication token
            verify_ssl: SSL certificate verification (default: from env or True)
            **kwargs: Additional session configuration
        """
        self.token = token
        self.base_url = base_url.rstrip('/')

        # Determine SSL verification setting
        if verify_ssl is None:
            env_verify = os.environ.get('DSS_VERIFY_SSL', 'true').lower()
            verify_ssl = env_verify in ('true', '1', 'yes', 'on')

        self.verify_ssl = verify_ssl

        if not self.verify_ssl:
            # Only disable warnings locally when SSL verification is explicitly disabled
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning(
                "SSL certificate verification is DISABLED. This is insecure and should only be used "
                "for testing or with self-signed certificates in trusted networks."
            )
            logger.warning(
                "SSL verification is DISABLED for %s - this is a security risk!",
                self.base_url
            )

        # Create session with connection pooling
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

        # Configure retry strategy - optimized for Raspberry Pi (fewer retries, faster backoff)
        retry_strategy = Retry(
            total=2,  # Reduced from 3 to 2 for faster failure handling
            backoff_factor=0.2,  # Reduced from 0.5 for faster retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PATCH"]
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Apply additional kwargs
        for arg, value in kwargs.items():
            if isinstance(value, dict):
                value = self.__deep_merge(getattr(self.session, arg, {}), value)
            setattr(self.session, arg, value)

    @REQUEST_TIME.time()
    @retry_on_failure(max_retries=2, backoff_factor=0.2)
    def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Perform GET request with retry logic.
        
        Args:
            url: URL path (will be appended to base_url)
            **kwargs: Additional request parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.exceptions.RequestException: If request fails after retries
        """
        # Ensure verify is set (can be overridden in kwargs)
        if 'verify' not in kwargs:
            kwargs['verify'] = self.verify_ssl

        try:
            response = self.session.get(
                self.base_url + url,
                headers=self.session.headers,
                **kwargs
            )
            response.raise_for_status()
            request_counter.labels(status_code=response.status_code).inc()

            return response.json()
        except requests.exceptions.SSLError as e:
            if isinstance(e.args[0], ssl.SSLError) and 'CERTIFICATE_VERIFY_FAILED' in str(e):
                logger.error(
                    "SSL certificate verification failed for %s. "
                    "This usually happens with self-signed certificates. "
                    "To disable SSL verification, set environment variable: DSS_VERIFY_SSL=false",
                    self.base_url
                )
            raise
        except requests.exceptions.HTTPError as e:
            request_counter.labels(status_code=e.response.status_code).inc()
            logger.error(
                "HTTP error %d for GET %s: %s",
                e.response.status_code,
                url,
                e.response.text[:200] if e.response.text else "No response body"
            )
            raise
        except requests.exceptions.JSONDecodeError as e:
            logger.error("Failed to decode JSON response from %s: %s", url, e)
            raise

    @REQUEST_TIME.time()
    @retry_on_failure(max_retries=2, backoff_factor=0.2)
    def post(self, url: str, **kwargs) -> requests.Response:
        """
        Perform POST request with retry logic.
        
        Args:
            url: URL path (will be appended to base_url)
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            requests.exceptions.RequestException: If request fails after retries
        """
        # Ensure verify is set (can be overridden in kwargs)
        if 'verify' not in kwargs:
            kwargs['verify'] = self.verify_ssl

        try:
            response = self.session.post(
                self.base_url + url,
                headers=self.session.headers,
                **kwargs
            )
            response.raise_for_status()
            request_counter.labels(status_code=response.status_code).inc()

            return response
        except requests.exceptions.SSLError as e:
            if isinstance(e.args[0], ssl.SSLError) and 'CERTIFICATE_VERIFY_FAILED' in str(e):
                logger.error(
                    "SSL certificate verification failed for %s. "
                    "This usually happens with self-signed certificates. "
                    "To disable SSL verification, set environment variable: DSS_VERIFY_SSL=false",
                    self.base_url
                )
            raise
        except requests.exceptions.HTTPError as e:
            request_counter.labels(status_code=e.response.status_code).inc()
            logger.error(
                "HTTP error %d for POST %s: %s",
                e.response.status_code,
                url,
                e.response.text[:200] if e.response.text else "No response body"
            )
            raise

    @REQUEST_TIME.time()
    @retry_on_failure(max_retries=2, backoff_factor=0.2)
    def patch(self, url: str, **kwargs) -> requests.Response:
        """
        Perform PATCH request with retry logic.
        
        Args:
            url: URL path (will be appended to base_url)
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            requests.exceptions.RequestException: If request fails after retries
        """
        # Ensure verify is set (can be overridden in kwargs)
        if 'verify' not in kwargs:
            kwargs['verify'] = self.verify_ssl

        try:
            response = self.session.patch(
                self.base_url + url,
                headers=self.session.headers,
                **kwargs
            )
            response.raise_for_status()
            request_counter.labels(status_code=response.status_code).inc()

            return response
        except requests.exceptions.SSLError as e:
            if isinstance(e.args[0], ssl.SSLError) and 'CERTIFICATE_VERIFY_FAILED' in str(e):
                logger.error(
                    "SSL certificate verification failed for %s. "
                    "This usually happens with self-signed certificates. "
                    "To disable SSL verification, set environment variable: DSS_VERIFY_SSL=false",
                    self.base_url
                )
            raise
        except requests.exceptions.HTTPError as e:
            request_counter.labels(status_code=e.response.status_code).inc()
            logger.error(
                "HTTP error %d for PATCH %s: %s",
                e.response.status_code,
                url,
                e.response.text[:200] if e.response.text else "No response body"
            )
            raise

    @REQUEST_TIME.time()
    @retry_on_failure(max_retries=2, backoff_factor=0.2)
    def get_token(self, api: str) -> str:
        """
        Get application token from digitalStrom API.
        
        Args:
            api: API endpoint path
            
        Returns:
            Authentication token string
            
        Raises:
            requests.exceptions.RequestException: If request fails after retries
            KeyError: If response doesn't contain expected token
        """
        param = {"loginToken": f"{self.token}"}

        try:
            response = self.session.get(
                self.base_url + api + "/loginApplication",
                headers=self.session.headers,
                params=param,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            request_counter.labels(status_code=response.status_code).inc()

            result = response.json()
            return result['result']['token']
        except requests.exceptions.SSLError as e:
            if isinstance(e.args[0], ssl.SSLError) and 'CERTIFICATE_VERIFY_FAILED' in str(e):
                logger.error(
                    "SSL certificate verification failed for %s. "
                    "This usually happens with self-signed certificates. "
                    "To disable SSL verification, set environment variable: DSS_VERIFY_SSL=false",
                    self.base_url
                )
            raise
        except KeyError as e:
            logger.error("Token not found in response: %s",
                         response.json() if 'response' in locals() else "No response")
            raise
        except requests.exceptions.HTTPError as e:
            request_counter.labels(status_code=e.response.status_code).inc()
            logger.error(
                "HTTP error %d while getting token: %s",
                e.response.status_code,
                e.response.text[:200] if e.response.text else "No response body"
            )
            raise

    @staticmethod
    def __deep_merge(source: Dict, destination: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        Args:
            source: Source dictionary
            destination: Destination dictionary (will be modified)
            
        Returns:
            Merged dictionary
        """
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                RequestHandler.__deep_merge(value, node)
            else:
                destination[key] = value
        return destination
