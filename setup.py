#!/usr/bin/env python

"""The setup script."""

try:
    from setuptools import setup, find_packages
except ImportError:
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
    from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "opencv-python",
    "pyperclip",
    "easyocr",
    "Pillow",
    "numpy",
    "typer",
    "pysimdjson",
    "screeninfo",
]

test_requirements = []

setup(
    author="Vladimir Vilimaitis",
    author_email="vladimirvilimaitis@gmail.com",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    description="DotA 2 Roshan death timer macros, using computer vision.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="dota_2_rosh_timer",
    name="dota_2_rosh_timer",
    packages=find_packages(include=["dota_2_rosh_timer", "dota_2_rosh_timer.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/vovavili/dota_2_rosh_timer",
    version="1.0.0",
    zip_safe=False,
)
