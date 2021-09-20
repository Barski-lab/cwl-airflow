#! /usr/bin/env python3
import os
import subprocess
import time
from setuptools import setup, find_packages


GIT_VERSION_FILE = os.path.join("cwl_airflow","git_version")
HERE = os.path.abspath(os.path.dirname(__file__))


def get_git_tag():
    return subprocess.check_output(["git", "describe", "--contains"], text=True).split("^")[0].strip()


def get_git_timestamp():
    gitinfo = subprocess.check_output(
        ["git", "log", "--first-parent", "--max-count=1", "--format=format:%ct", "."], text=True).strip()
    return time.strftime("%Y%m%d%H%M%S", time.gmtime(int(gitinfo)))


def get_description():
    README = os.path.join(HERE, "README.md")
    with open(README, "r") as f:
        return f.read()


def get_version():
    """
    Tries to get pachage version with following order:
    0. default version
    1. from git_version file - when installing from pip, this is the only source to get version
    2. from tag
    3. from commit timestamp
    Updates/creates git_version file with the package version
    :return: package version
    """
    version = "1.2.0"                                      # set default version
    try:
        with open(GIT_VERSION_FILE, "r") as input_stream:  # try to get version info from file
            version = input_stream.read()
    except Exception:
        pass
    try:
        version = get_git_tag()                            # try to get version info from the closest tag
    except Exception:
        try:
            version = "1.2." + get_git_timestamp()         # try to get version info from commit date
        except Exception:
            pass
    try:
        with open(GIT_VERSION_FILE, "w") as output_stream: # save updated version to file (or the same)
            output_stream.write(version)
    except Exception:
        pass
    return version


EXTRAS_REQUIRE = {
    "celery": [
        "celery~=4.4.2",
        "flower>=0.7.3, <1.0",
        "vine~=1.3"
    ],
    "mysql": [
        "mysql-connector-python>=8.0.11, <=8.0.22",
        "mysqlclient>=1.3.6,<3",
    ],
    "statsd": [
        "statsd>=3.3.0, <4.0"
    ],
    "rabbitmq": [
        "amqp<5.0.0"
    ],
    "postgres": [
        "psycopg2-binary>=2.7.4"
    ]
}


setup(
    name="cwl-airflow",
    description="Python package to extend Airflow functionality with CWL v1.1 support",
    long_description=get_description(),
    long_description_content_type="text/markdown",
    version=get_version(),
    url="https://github.com/Barski-lab/cwl-airflow",
    download_url="https://github.com/Barski-lab/cwl-airflow",
    author="Michael Kotliar",
    author_email="misha.kotliar@gmail.com",
    license="Apache-2.0",
    include_package_data=True,
    packages=find_packages(
        exclude=["docs", "tests", "dev"]
    ),
    extras_require=EXTRAS_REQUIRE,
    install_requires=[
        "apache-airflow==2.1.4",
        "cwltool==3.1.20210816212154",
        "cwltest==2.1.20210626101542",
        "jsonmerge",
        "connexion",
        "tornado",
        "docker",
        "swagger-ui-bundle"
    ],
    zip_safe=False,
    scripts=["cwl_airflow/bin/cwl-airflow"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Healthcare Industry",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Scientific/Engineering :: Medical Science Apps."
    ]
)
