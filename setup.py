import os
import subprocess
import time
from setuptools import setup, find_packages


def get_git_tag():
    return subprocess.check_output(['git', 'describe', '--contains']).strip()


def get_git_timestamp():
    gitinfo = subprocess.check_output(
        ['git', 'log', '--first-parent', '--max-count=1',
         '--format=format:%ct', '.']).strip()
    return time.strftime('%Y%m%d%H%M%S', time.gmtime(int(gitinfo)))


def get_version():
    version = '1.0.0'  # default version
    try:
        version = get_git_tag()            # try to get version info from the closest tag
    except subprocess.CalledProcessError:
        try:
            version = '1.0.' + get_git_timestamp()  # try to get version info from commit date
        except subprocess.CalledProcessError:
            pass
    return version


setup(
    name='cwl-airflow',
    description='Python package to extend Airflow functionality with CWL v1.0 support',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    version=get_version(),
    url='https://github.com/Barski-lab/cwl-airflow',
    download_url='https://github.com/Barski-lab/cwl-airflow',
    author='Michael Kotliar',
    author_email='misha.kotliar@gmail.com',
    license = 'Apache-2.0',
    packages=find_packages(),
    install_requires=[
        'cwltool==1.0.20180116213856',
        'jsonmerge',
        'mysql-python>=1.2.5',
        'ruamel.yaml<0.15',
        "apache-airflow==1.8.2",
        "html5lib"
    ],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            "cwl-airflow-runner=cwl_runner.main:main",
            "cwl-runner=cwl_runner.main:main"
        ]
    }
)