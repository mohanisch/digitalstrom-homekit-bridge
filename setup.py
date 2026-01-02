import io
from pathlib import Path

from setuptools import find_packages
from setuptools import setup


def get_version():
    """Read version from VERSION file."""
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        with open(version_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "2.3.0"


with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

setup(
    name="dsbridge",
    version=get_version(),
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
