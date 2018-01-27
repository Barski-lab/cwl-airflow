from setuptools import setup, find_packages
import setuptools.command.egg_info as egg_info_cmd
import os

try:
    import gittaggers
    tagger = gittaggers.EggInfoFromGit
except ImportError:
    tagger = egg_info_cmd.egg_info

setup(
    name='cwl-airflow',
    description='Python package to extend Airflow functionality with CWL v1.0 support',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    version='1.0.0',
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
    cmdclass={'egg_info': tagger},
    entry_points={
        'console_scripts': [
            "cwl-airflow-runner=cwl_runner.main:main",
            "cwl-runner=cwl_runner.main:main"
        ]
    }
)