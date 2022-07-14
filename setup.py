import io

from setuptools import find_packages
from setuptools import setup

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

setup(
    name="dsbridge",
    version="2.0.2",
    url="",
    maintainer="Marco Hanisch",
    maintainer_email="marco.hanisch@webkompleks.de",
    description="Controlling your digitalStrom home via iOS.",
    long_description=readme,
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "dsbridge = dsbridge.__main__:main",
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
                      "PyYAML",
                      "Flask",
                      "waitress",
                      "base36"],
    zip_safe=False
)
