from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.egg_info import egg_info
from subprocess import check_call
import os


class PostInstallCommand(install):
    """Post-installation for installation mode"""
    def run(self):
        check_call("./install.sh".split())
        install.run(self)

class PostEggInfoCommand(egg_info):
    """Post-installation for egg_info mode"""
    def run(self):
        check_call("./install.sh".split())
        egg_info.run(self)

setup(
    name='cwl-airflow',
    description='Python package to extend Airflow functionality with CWL v1.0 support',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    version='1.0.0',
    url='https://github.com/Barski-lab/cwl-airflow',
    download_url=('https://github.com/Barski-lab/cwl-airflow'),
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
    zip_safe=False,
    cmdclass={
        'install': PostInstallCommand,
        'egg_info': PostEggInfoCommand
    },
    entry_points={
        'console_scripts': [
            "cwl-airflow-runner=cwl_runner.main:main",
            "cwl-runner=cwl_runner.main:main"
        ]
    }
)