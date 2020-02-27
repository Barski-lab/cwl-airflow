
# From cwl-airflow-1.0.16

## Packaging and distributing
### Using pyinstaller
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

### Build AppImage

On the clean virtual machine with Ubuntu 16.04.4
1. Install pip 
```bash
sudo apt install python3-pip
```
2. Create AppImage
```bash
./build_app_image.sh
```

### Build portable version for Ubuntu

On the machine with Docker installed
1. Run `pack_ubuntu.sh` from the dev folder
```bash
./pack_ubuntu.sh
```


### Build Vagrant Box
1. Install Vagrant from [here](https://www.vagrantup.com/downloads.html)
2. Install VirtualBox from [here](https://www.virtualbox.org/wiki/Downloads)
3. Download Ubuntu 16.04 Server image from [here](http://releases.ubuntu.com/16.04/)
4. Create new virtual machine
    - name: cwl-airflow-production
    - type: Linux
    - version: Ubuntu (64 bit)
    - memory: 4096 MB
    - disk: VMDK, dynamically allocated up to 256.00 GB
5. Install Ubuntu 16.04 Server on the cwl-airflow virtual machine
    - hostname: cwl-airflow-production
    - user: vagrant
    - password: vagrant
    - encryption: no
    - software:
      - standard system utilities
9. Install OpenSSH Server
   ```
   sudo apt-get install -y openssh-server
   ```
6. Login  throught ssh (set up port forwarding in VM)
6. Install Guest Additions
    ```
    sudo apt-get install linux-headers-$(uname -r) build-essential dkms
    sudo reboot
    ```
    Click Devices / Insert Guest Additions CD image
    ```
    sudo mount /dev/cdrom /media/cdrom
    sudo sh /media/cdrom/VBoxLinuxAdditions.run
    sudo reboot
    ```
7. Add the vagrant user to sudoers file
   ```
   sudo visudo
   ```
   Add line
   ```
   vagrant ALL=(ALL) NOPASSWD:ALL
   ```
8. Install Vagrant Public Keys
   ```
   cd
   mkdir .ssh
   cd .ssh
   wget https://raw.githubusercontent.com/hashicorp/vagrant/master/keys/vagrant.pub -O authorized_keys
   chmod 0600 authorized_keys
   cd ..
   chmod 0700 .ssh
   chown -R vagrant .ssh
   ```
10. Configure OpenSSH Server
    ```
    sudo vi /etc/ssh/sshd_config
    ```
    Add/Update the following fields
    ```
    Port 22
    PubkeyAuthentication yes
    AuthorizedKeysFile %h/.ssh/authorized_keys
    PermitEmptyPasswords no
    UseDNS no
    ```
    Restart ssh service
    ```
    sudo service ssh restart
    ```
12. Install RabbitMQ (some useful info is [here](http://site.clairvoyantsoft.com/installing-rabbitmq/))
    ```
    sudo apt-get install rabbitmq-server
    ```
    Enable Web Interface
    ```
    sudo rabbitmq-plugins enable rabbitmq_management
    ```
    Create configuration file `/etc/rabbitmq/rabbitmq.config` as root
    ```
    [
    {rabbit,
      [
      {loopback_users, []}
      ]}
    ].
    ```
12. Install mysql-server, then stop it and disable (follow the link [here](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-16-04))
    ```
    sudo apt-get install mysql-server
    ```
    Set root password to `vagrant`
    ```
    mysql_secure_installation
    ```
    - remove test database and access to it - Yes
    - remove anonymous users - Yes
    - disallow root login remotely - Yes
    - reload privilege table now - Yes
    ```
    mysql -u root -p
    ```
    We need to allow airflow user to login from other hosts (see [here](https://stackoverflow.com/questions/10236000/allow-all-remote-connections-mysql))
    ```sql
    CREATE DATABASE airflow;
    CREATE USER 'airflow'@'localhost' IDENTIFIED BY 'airflow';
    CREATE USER 'airflow'@'%' IDENTIFIED BY 'airflow';
    GRANT ALL PRIVILEGES ON airflow.* TO 'airflow'@'localhost';
    GRANT ALL PRIVILEGES ON airflow.* TO 'airflow'@'%';
    ```
    Also, update `/etc/mysql/mysql.conf.d/mysqld.cnf` to include
    ```
    bind-address          = 0.0.0.0
    # skip-external-locking
    ```
    We also need to install mysqlclient (cannot find mysql_config without it)
    ```
    sudo apt-get install libmysqlclient-dev
    ```
1. Install pip 
   ```bash
   sudo apt install python3-pip
   pip3 install --upgrade pip
   ```
   Maybe you will need to log out / login to fix pip problem
13. Update Airflow to include mysql and celery with all their dependencies
    ```
    pip3 install -U apache-airflow[mysql,celery,rabbitmq]==1.9.0 --user
    ```
14. Run Airflow to generate default configuration file
    ```
    airflow
    ```
15. Make sure you have py-amqp (read [here](https://stackoverflow.com/questions/51824929/airflow-scheduler-failure))
    ```
    pip3 install amqp
    ```
15. Install cwl-airflow python package following instructions from readme
    ```
    pip3 install cwl-airflow --user
    ```
16. Install docker [link](https://docs.docker.com/install/linux/docker-ce/ubuntu/)
16. Pull all docker images for cwl-airflow examples, including hello-world docker image
    ```
    docker run hello-world
    cd /home/vagrant/.local/lib/python3.5/site-packages/cwl_airflow/tests/cwl
    grep -r dockerPull . | cut -d" " -f 4 | sort -u | xargs -L 1 docker pull
    ```
17. Create the following files as root
    
    /etc/systemd/system/airflow-webserver.service
    ```
    [Unit]
    Description=Airflow webserver daemon
    After=network.target mysql.service rabbitmq-server.service
    Wants=mysql.service rabbitmq-server.service

    [Service]
    User=vagrant
    EnvironmentFile=/etc/default/airflow
    WorkingDirectory=/home/vagrant/airflow
    KillMode=control-group
    ExecStart=/home/vagrant/.local/bin/airflow webserver
    ExecStop=/bin/kill -s QUIT $MAINPID
    Restart=on-failure
    RestartSec=10s

    [Install]
    WantedBy=multi-user.target
    ```
    
    /etc/systemd/system/airflow-scheduler.service
    ```
    [Unit]
    Description=Airflow scheduler daemon
    After=network.target mysql.service rabbitmq-server.service docker.service
    Wants=mysql.service rabbitmq-server.service docker.service

    [Service]
    User=vagrant
    EnvironmentFile=/etc/default/airflow
    WorkingDirectory=/home/vagrant/airflow
    KillMode=control-group
    ExecStart=/home/vagrant/.local/bin/airflow scheduler
    ExecStop=/bin/kill -s QUIT $MAINPID
    Restart=on-failure
    RestartSec=10s

    [Install]
    WantedBy=multi-user.target
    ```

    /etc/systemd/system/airflow-worker.service
    ```
    [Unit]
    Description=Airflow celery worker daemon
    After=network.target mysql.service rabbitmq-server.service docker.service
    Wants=mysql.service rabbitmq-server.service docker.service

    [Service]
    User=vagrant
    EnvironmentFile=/etc/default/airflow
    WorkingDirectory=/home/vagrant/airflow
    KillMode=control-group
    ExecStart=/home/vagrant/.local/bin/airflow worker
    ExecStop=/bin/kill -s QUIT $MAINPID
    Restart=on-failure
    RestartSec=10s

    [Install]
    WantedBy=multi-user.target
    ```

    /etc/systemd/system/airflow-flower.service
    ```
    [Unit]
    Description=Airflow flower daemon
    After=network.target mysql.service rabbitmq-server.service
    Wants=mysql.service rabbitmq-server.service

    [Service]
    User=vagrant
    EnvironmentFile=/etc/default/airflow
    WorkingDirectory=/home/vagrant/airflow
    KillMode=control-group
    ExecStart=/home/vagrant/.local/bin/airflow flower
    ExecStop=/bin/kill -s QUIT $MAINPID
    Restart=on-failure
    RestartSec=10s

    [Install]
    WantedBy=multi-user.target
    ```
    /etc/default/airflow
    ```
    PATH=/home/vagrant/bin:/home/vagrant/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:$PATH
    ```
    Reload systemd
    ```
    sudo systemctl daemon-reload
    ```
18. Install latest LTS nodejs and npm (link [here](https://www.digitalocean.com/community/tutorials/how-to-install-node-js-on-ubuntu-16-04))
    ```
    curl -sL https://deb.nodesource.com/setup_8.x -o nodesource_setup.sh
    sudo bash nodesource_setup.sh
    sudo apt-get install nodejs
    ```
19. Reboot machine
    ```
    sudo reboot
    ```
19. Make sure to set Network / Adapter 1 to NAT for cwl-airflow virtual machine
20. Package cwl-airflow virtual machine to file
    ```
    vagrant package --base cwl-airflow-production --output cwl_airflow_production.box
    ```
21. The system doesn't work witohout access to the internet (docker pull return 1)

## Queues

To define the queues for Celery Executor update `airflow.cfg` with the path to the YAML file describing the queues.
```
[cwl]
queues = path/to/the/queues.yaml
```
queues.yaml
```yaml
advanced:
  cpus: 2
  ram: 2048
default:
  cpus: 1
  ram: 1024
```

# From cwl-airflow-parser

---

## Table of Contents

* [Posting status updates](#posting-status-updates)
* [Triggering DAGs through API](#triggering-dags-through-api)
* [Check JWT signature when triggering DAG](#check-jwt-signature-when-triggering-dag)
* [Stopping DagRun](#stopping-dagrun)
* [CI with Travis](#ci-with-travis)
---

### Posting progress, task status and DagRun results

Progress, task status and DagRun results are posted to the different routes that are defined in
 `./utils/notifier.py` as
```
ROUTES = {
  "progress": "progress",
  "results":  "results",
  "status":   "status"
}
```

    Progress is posted when:
    - task finished successfully
    - dag finished successfully
    - dag failed

    Task status is posted when:
    - task started to run
    - task finished successfully
    - task failed
    - task is set to retry

    Results are posted when:
    - dag finished successfully


1. Add new Connection
    - Conn Id `process_report`
    - Conn Type `HTTP`
    - Host `localhost` or any other
    - Port `80` or any other
    - Extra `{"endpoint": "satellite/v1/"}` or any other
    
2. If JWT signature is required
    - Add Variables
        - `process_report_private_key`
        - `process_report_algorithm`

3. Test posting progress, task status and DagRun results
   ```
   python ./utils/server.py [PORT]
   ```
   Script will listen to the port `8080` (by default) on `localhost` and try to verify data with hardcoded `public_key`

4. JSON object structure
   
   Progress
   ```yaml
   {
     "payload": {
       "state":           # DagRun state. One of ["success", "running", "failed"]
       "dag_id":          # string                                   
       "run_id":          # string
       "progress":        # int from 0 to 100 percent               
       "error":           # if not "", then includes the reason of the failure as a string                 
     }
   }
   ```      
   Task status
   ```yaml
   {
     "payload": {
       "state":           # Task state. One of ["success", "running", "failed", "up_for_retry", "upstream_failed"]
       "dag_id":          # string                                   
       "run_id":          # string
       "task_id":         # string               
     }
   }
   ```   

   DagRun results
   ```yaml
   {
     "payload": {
       "dag_id":          # string                                   
       "run_id":          # string
       "results":         # JSON object to include outputs from CWL workflow               
     }
   }
   ```   

   When JWT signature is used, payload includes JWT token:
   ```yaml
   {
     "payload": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJkYWdfaWQiOiJzbGVlcF9mb3JfYW5faG91cl9jd2xfZG9ja2VyIiwicnVuX2lkIjoicnVuXzQiLCJleGVjdXRpb25fZGF0ZSI6IjIwMTgtMTItMTEgMTc6MzA6MTAiLCJzdGFydF9kYXRlIjoiMjAxOC0xMi0xMSAxNzozMDoxMCIsImVuZF9kYXRlIjpudWxsLCJzdGF0ZSI6InJ1bm5pbmciLCJ0YXNrcyI6W3sidGFza19pZCI6IkNXTEpvYkRpc3BhdGNoZXIiLCJzdGFydF9kYXRlIjoiMjAxOC0xMi0xMSAxNzozMDoxMiIsImVuZF9kYXRlIjpudWxsLCJzdGF0ZSI6InJ1bm5pbmciLCJ0cnlfbnVtYmVyIjoxLCJtYXhfdHJpZXMiOjB9LHsidGFza19pZCI6IkNXTEpvYkdhdGhlcmVyIiwic3RhcnRfZGF0ZSI6bnVsbCwiZW5kX2RhdGUiOm51bGwsInN0YXRlIjpudWxsLCJ0cnlfbnVtYmVyIjoxLCJtYXhfdHJpZXMiOjB9LHsidGFza19pZCI6InNsZWVwXzEiLCJzdGFydF9kYXRlIjpudWxsLCJlbmRfZGF0ZSI6bnVsbCwic3RhdGUiOm51bGwsInRyeV9udW1iZXIiOjEsIm1heF90cmllcyI6MH0seyJ0YXNrX2lkIjoic2xlZXBfMiIsInN0YXJ0X2RhdGUiOm51bGwsImVuZF9kYXRlIjpudWxsLCJzdGF0ZSI6bnVsbCwidHJ5X251bWJlciI6MSwibWF4X3RyaWVzIjowfSx7InRhc2tfaWQiOiJzbGVlcF8zIiwic3RhcnRfZGF0ZSI6bnVsbCwiZW5kX2RhdGUiOm51bGwsInN0YXRlIjpudWxsLCJ0cnlfbnVtYmVyIjoxLCJtYXhfdHJpZXMiOjB9LHsidGFza19pZCI6InNsZWVwXzQiLCJzdGFydF9kYXRlIjpudWxsLCJlbmRfZGF0ZSI6bnVsbCwic3RhdGUiOm51bGwsInRyeV9udW1iZXIiOjEsIm1heF90cmllcyI6MH0seyJ0YXNrX2lkIjoic2xlZXBfNSIsInN0YXJ0X2RhdGUiOm51bGwsImVuZF9kYXRlIjpudWxsLCJzdGF0ZSI6bnVsbCwidHJ5X251bWJlciI6MSwibWF4X3RyaWVzIjowfSx7InRhc2tfaWQiOiJzbGVlcF82Iiwic3RhcnRfZGF0ZSI6bnVsbCwiZW5kX2RhdGUiOm51bGwsInN0YXRlIjpudWxsLCJ0cnlfbnVtYmVyIjoxLCJtYXhfdHJpZXMiOjB9XX0.dI4TPzGyZdUkCct5EfKurJKRbQ-RXTI8NT4ZHKA47hUYep1rR8hnnGX0GsSK-UWTqGKNDHnGYAR2jVqgH0_AJVIAEZLPqBQZ_oxxddvhb-_vuwy72pCdC4mA2EYVlrdA6nNmplwEJ2u4eLAy9OKN6RuI83PIRuPrH8cXMZRjC-A"
   }
   ```


### Triggering DAGs through API
1. Run `airflow webserver`
2. Trigger DAG through API
   - Using `curl`
     Test triggering DAGs through API (set correct `DAG_ID` and `RUN_ID`)
     ```
     curl --header "Content-Type: application/json" \
          --request POST \
          --data '{"run_id":"RUN_ID","conf":"{\"job\":{\"output_folder\":\"/your/output/folder\"}}"}' \
          http://localhost:8080/api/experimental/dags/{DAG_ID}/dag_runs
     ```
   - Using `trigger.py`
     ```bash
     python ./utils/trigger.py -d DAG_ID -r RUN_ID -c "{\"job\":{\"output_folder\":\"/your/output/folder\"}}"
     ```
     
     Script will try to post JSON data to the following URL (by default)
     `http://localhost:8080/api/experimental/dags/{DAG_ID}/dag_runs`
   
     JSON data have the following structure
     ```yaml
     json_data = {
          "run_id": RUN_ID,
          "conf": "{\"job\":{\"output_folder\":\"/your/output/folder\"}}"
          "token": "jwt token"
     }
     ```
     Where `token` is generated by JWT from the object that includes only `run_id` and `conf` fields
     using hardcoded `private_key` and `RS256` algorithm (by default)
    
### Check JWT signature when triggering DAG
1. Update `airflow.cfg`
   ```
   auth_backend = cwl_airflow_parser.utils.jwt_backend
   ```
2. Add Variables
    - `jwt_backend_public_key`
    - `jwt_backend_algorithm`
3. Test trigger DAG through API (using `trigger.py`)

 
### Stopping DagRun 
1. Copy `./utils/dags/clean_dag_run.py` into the dag folder
2. Trigger `clean_dag_run` with `remove_dag_id` and `remove_run_id` parameters set in `--conf`
   ```bash
   airflow trigger_dag -r RUN_ID -c "{\"remove_dag_id\":\"some_dag_id\", \"remove_run_id\":\"some_run_id\"}" clean_dag_run
   ```
   or
   ```bash
   curl --header "Content-Type: application/json" \
        --request POST \
        --data '{"run_id":"RUN_ID","conf":"{\"remove_dag_id\":\"some_dag_id\", \"remove_run_id\":\"some_run_id\"}"}' \
        http://localhost:8080/api/experimental/dags/clean_dag_run/dag_runs
   ```
   or (in case using JWT singature)
   ```bash
   python3.6 ./utils/trigger.py -d clean_dag_run -r RUN_ID -c "{\"remove_dag_id\":\"some_dag_id\", \"remove_run_id\":\"some_run_id\"}"
   ```
  
   Note
   - `clean_dag_run` will indicate successfull execution in case
        - `remove_dag_id` & `remove_run_id` are not found in DB
        - dagrun that corresponds to `remove_dag_id` & `remove_run_id` doen't have any tasks that
          have active PIDs
        - all active PIDs of dagrun's tasks are properly killed
   - `clean_dag_run` will indicate FAIL in case
        - after setting `Failed` state to all the tasks of the specific dagrun (defined by `remove_dag_id` & `remove_run_id`)
        we waited to long for scheduler to kill their PIDs. Timeout is equal to `2 * KILLED_TASK_CLEANUP_TIME` from
        `airflow.cfg`
   - `clean_dag_run` doesn't know if any of the tasks' PID children are stopped too 

### CI with Travis
1. Experimental `.travis.yml` configuration file has the following structure
   - runs two jobs separately (see `env`) with different tests to run (see `NTEST`)
   - to use `LocalExecutor` mysql-server is started in docker
   - `airflow.cfg` is updated to unpause all dags
   - `scheduler` and `webserver` are started in background
   - `cwl-airflow-tester` is run with `-s` argument to display spinner and prevent
     Travis from killing the job after being idle for more than 10 min