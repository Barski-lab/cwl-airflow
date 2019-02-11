[![Build Status](https://travis-ci.org/Barski-lab/cwl-airflow.svg?branch=master)](https://travis-ci.org/Barski-lab/cwl-airflow) -  **Travis CI**  
[![Build Status](https://ci.commonwl.org/buildStatus/icon?job=airflow-conformance)](https://ci.commonwl.org/job/airflow-conformance) - **CWL conformance tests**  

# Packaging and distributing
## Using pyinstaller
- Use **Python 3.6.5** on Mac (Darwin-18.2.0-x86_64-i386-64bit)
- Follow this link [Make sure everything is packaged correctly](https://github.com/pyinstaller/pyinstaller/wiki/How-to-Report-Bugs#make-sure-everything-is-packaged-correctly)
and get the latest devel version of **pyinstaller**
    ```bash
    pip install https://github.com/pyinstaller/pyinstaller/archive/develop.zip
    ```
- Run **pyinstaller** pointing to the **main.py**
    ```bash
    pyinstaller --onedir ./cwl-airflow/cwl_airflow/main.py
    ```
- Get an error with **urllib3.packages.six.moves**
    ```bash
    28465 INFO: Processing pre-safe import module hook   urllib3.packages.six.moves
    Traceback (most recent call last):
      File "<string>", line 2, in <module>
      File "/usr/local/lib/python3.6/site-packages/urllib3/__init__.py", line 8, in <module>
        from .connectionpool import (
      File "/usr/local/lib/python3.6/site-packages/urllib3/connectionpool.py", line 35, in <module>
        from .request import RequestMethods
      File "/usr/local/lib/python3.6/site-packages/urllib3/request.py", line 3, in <module>
        from .filepost import encode_multipart_formdata
      File "/usr/local/lib/python3.6/site-packages/urllib3/filepost.py", line 4, in <module>
        from uuid import uuid4
      File "/usr/local/lib/python3.6/site-packages/uuid.py", line 138
        if not 0 <= time_low < 1<<32L:
                                    ^
    SyntaxError: invalid syntax
    pre-safe-import-module hook failed, needs fixing.
    ```
- Find some other tool for packaging
