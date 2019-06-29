# Troubleshooting

Most of the problems are already handled by *cwl-airflow* itself. User is provided
with the full explanation and ways to correct them through the console output. Additional
information regarding the failed workflow steps, can be found in the task execution logs
that are accessible through Airflow Webserver UI. 

Common errors and ways to fix them
- ***`cwl-airflow` is not found*** 
   
   Perhaps, you have installed it with *--user* option and your *PATH*
   variable doesn't include your user based Python *bin* folder.
   Update *PATH* with the following command
   ```sh
   export PATH="$PATH:`python -m site --user-base`/bin"
   ```
- ***Fails to install on the latest Python 3.7.0***
  
  Unfortunatelly *Apache-Airflow 1.9.0* cannot be properly installed on the latest *Python 3.7.0*.
  Consider using *Python 3.6* or *2.7* instead.
  
  macOS users can install Python 3.6.5 (instead of the latest Python 3.7.0) with the following command
  (explained [here](https://stackoverflow.com/a/51125014/8808721))
  ```bash
    brew install https://raw.githubusercontent.com/Homebrew/homebrew-core/f2a764ef944b1080be64bd88dca9a1d80130c558/Formula/python.rb
  ```

- ***Fails to compile ruamel.yaml***
   
  Perhaps, you should update your *setuptools*. Consider using *--user* if necessary.
  If installing on macOS brewed Python *--user* **should not** be used (explained [here](https://docs.brew.sh/Homebrew-and-Python))
  ```bash
  pip install -U setuptools # --user
  ```
  `--user` - explained in [Installation](./installation.md) section
  
- ***Docker is unable to pull images from the Internet***

  If you are using proxy, your Docker should be configured properly too.
  Refer to the official [documentation](https://docs.docker.com/config/daemon/systemd/#httphttps-proxy)
   
- ***Docker is unable to mount directory***

  For macOS docker has a list of directories that it's allowed to mount by default. If your input files are located in
  the directories that are not included in this list, you are better of either changing the location of
  input files and updating your Job file or adding this directories into Docker configuration *Preferences / File Sharing*.

- ***Airflow Webserver displays missing DAGs***

  If some of the Job files have been manually deleted, they will be still present in Airflow database, hence they 
  will be displayed in Webserver's UI. Sometimes you may still see missing DAGs because of the inertness of Airflow
  Webserver UI.

- ***Airflow Webserver randomly fails to display some of the pages***

  When new DAG is added Airflow Webserver and Scheduler require some time to update their states.
  Consider using `cwl-airflow init -r 5 -w 4` to make Airflow Webserver react faster for all newly created DAGs.
  Or manualy update Airflow configuration file (default location is *~/airflow/airflow.cfg*) and restart both
  Webserver and Scheduler. Refer to the official documentation [here](https://airflow.apache.org/configuration.html) 
  
- ***Workflow execution fails***

  Make sure that CWL descriptor and Job files are correct. You can always check them with *cwltool*
  (trusted version 1.0.20180622214234)
  ```bash
  cwltool --debug WORKFLOW JOB
  ```