import io
from setuptools import find_packages
from setuptools import setup

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

setup(
    name="dsbridge",
    version="2.1.0",
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
    install_requires=["HAP-python[QRCode]==4.4.0",
                      "setuptools==65.6.3",
                      "PyQRCode~=1.2.1",
                      "fnvhash~=0.1.0",
                      "websocket~=0.2.1",
                      "websocket-client==1.4.2",
                      "urllib3==1.26.13",
                      "requests==2.28.1",
                      "rgbxy",
                      "PyYAML~=6.0",
                      "Flask~=2.2.2",
                      "waitress~=2.1.2",
                      "base36~=0.1.1"],
    zip_safe=False
)
