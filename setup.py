"""Python setup.py for fbapy package"""
import io
import os
from setuptools import find_packages, setup


def read(*paths, **kwargs):
    """Read the contents of a text file safely.
    >>> read("fbapy", "VERSION")
    '0.1.0'
    >>> read("README.md")
    ...
    """

    content = ""
    with io.open(
        os.path.join(os.path.dirname(__file__), *paths),
        encoding=kwargs.get("encoding", "utf8"),
    ) as open_file:
        content = open_file.read().strip()
    return content


def read_requirements(path):
    return [
        line.strip()
        for line in read(path).split("\n")
        if not line.startswith(('"', "#", "-", "git+"))
    ]


setup(
    name="fbapy",
    version="1.0.1",
    description="Unofficial Facebook Chat API for Python",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/RFS-ADRENO/fbapy",
    author="RFS-ADRENO (RDU), KhangPhan27 (KhangPhan)",
    packages=find_packages(exclude=["tests", ".github"]),
    install_requires=read_requirements("requirements.txt"),
    keywords=["facebook", "messenger", "chat", "api", "python", "unofficial"],
)
