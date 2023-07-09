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
    zip_safe=False
)
