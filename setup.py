import io

from setuptools import find_packages
from setuptools import setup

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

setup(
    name="digitalstrom-homekit-bridge",
    version="1.0.11",
    url="",
    maintainer="Marco Hanisch",
    maintainer_email="marco.hanisch@webkompleks.de",
    description="Controlling your digitalStrom home via iOS.",
    long_description=readme,
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "dsHomekit = dsHomekit.__main__:main",
        ]
    },
    install_requires=["websocket",
                      "websocket-client",
                      "pyhap",
                      "hap-python",
                      "fnvhash",
                      "pyqrcode",
                      "urllib3",
                      "requests",
                      "HAP-python[QRCode]",
                      "rgbxy",
                      "PyYAML"],
    zip_safe=False
)
