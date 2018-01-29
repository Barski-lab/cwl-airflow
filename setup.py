import os
import subprocess
import time
from setuptools import setup, find_packages


GIT_VERSION_FILE = os.path.join('cwl_airflow','git_version')


def get_git_tag():
    return subprocess.check_output(['git', 'describe', '--contains']).strip()


def get_git_timestamp():
    gitinfo = subprocess.check_output(
        ['git', 'log', '--first-parent', '--max-count=1',
         '--format=format:%ct', '.']).strip()
    return time.strftime('%Y%m%d%H%M%S', time.gmtime(int(gitinfo)))


def get_version():
    '''
    Tries to get pachage version with following order:
    0. default version
    1. from git_version file - when installing from pip, this is the only source to get version
    2. from tag
    3. from commit timestamp
    Updates/creates git_version file with the package version
    :return: package version 
    '''
    version = '1.0.0'                                      # set default version
    try:
        with open(GIT_VERSION_FILE, 'r') as input_stream:  # try to get version info from file
            version = input_stream.read()
    except IOError as ex:
        pass
    try:
        version = get_git_tag()                            # try to get version info from the closest tag
    except subprocess.CalledProcessError:
        try:
            version = '1.0.' + get_git_timestamp()         # try to get version info from commit date
        except subprocess.CalledProcessError:
            pass
    with open(GIT_VERSION_FILE, 'w') as output_stream:     # save updated version to file (or the same)
        output_stream.write(version)
    return version


setup(
    name='cwl-airflow',
    description='Python package to extend Airflow functionality with CWL v1.0 support',
    version=get_version(),
    url='https://github.com/Barski-lab/cwl-airflow',
    download_url='https://github.com/Barski-lab/cwl-airflow',
    author='Michael Kotliar',
    author_email='misha.kotliar@gmail.com',
    license = 'Apache-2.0',
    packages=find_packages(),
    package_data={'cwl_airflow': ['git_version']},
    include_package_data=True,
    install_requires=[
        'cwltool==1.0.20180116213856',
        'jsonmerge',
        'mysql-python>=1.2.5',
        'ruamel.yaml<0.15',
        "apache-airflow==1.8.2",
        "html5lib"
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            "cwl-airflow=cwl_airflow.main:main",
            "cwl-runner=cwl_airflow.main:main"
        ]
    }
)