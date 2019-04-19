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

## Build AppImage

On the clean virtual machine with Ubuntu 16.04.4
1. Install pip 
```bash
sudo apt install python3-pip
```
2. Create AppImage
```bash
./build_app_image.sh
```

## Build Vagrant Box
1. Install Vagrant from [here](https://www.vagrantup.com/downloads.html)
2. Install VirtualBox from [here](https://www.virtualbox.org/wiki/Downloads)
3. Download Ubuntu 16.04 Server image from [here](http://releases.ubuntu.com/16.04/)
4. Create new virtual machine
    - name: cwl-airflow
    - type: Linux
    - version: Ubuntu (64 bit)
    - memory: 4096 MB
    - disk: VMDK, dynamically allocated up to 268.00 GB
5. Install Ubuntu 16.04 Server on the cwl-airflow virtual machine
    - hostname: cwl-airflow
    - user: vagrant
    - password: vagrant
    - encryption: no
    - software:
      - standard system utilities
      - open-ssh server
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
9. Install OpenSSH Server
   ```
   sudo apt-get install -y openssh-server
   ```
10. Configure OpenSSH Server
    ```
    sudo vi /etc/ssh/sshd_config
    ```
    Add/Update the following fields
    ```
    Port 22
    PubKeyAuthentication yes
    AuthorizedKeysFile %h/.ssh/authorized_keys
    PermitEmptyPasswords no
    UseDNS no
    ```
    Restart ssh service
    ```
    sudo service ssh restart
    ```
11. DEPRECATED. USE RABBITMQ INSTEAD

    Install Redis, then stop it and disable (some useful links are [here](https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-redis-on-ubuntu-18-04) and [here](https://tecadmin.net/install-redis-ubuntu/))
    ```
    sudo apt-get install redis-server
    sudo systemctl stop redis-server.service
    sudo systemctl disable redis-server.service
    ```
    Update `/etc/redis/redis.conf` to include
    ```
    bind 0.0.0.0
    ```
12. Install RabbitMQ, then stop it and disable (some useful info is [here](http://site.clairvoyantsoft.com/installing-rabbitmq/))
    ```
    sudo apt-get install rabbitmq-server
    sudo systemctl stop rabbitmq-server.service
    sudo systemctl disable rabbitmq-server.service
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
    ```
    systemctl stop mysql.service
    systemctl disable mysql.service
    ```
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
16. Pull all docker images for cwl-airflow examples, including hello-world docker image
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
    After=network.target mysql.service rabbitmq-server.service
    Wants=mysql.service rabbitmq-server.service

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
    After=network.target mysql.service rabbitmq-server.service
    Wants=mysql.service rabbitmq-server.service

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
19. Make sure to set Network / Adapter 1 to NAT for cwl-airflow virtual machine
20. Package cwl-airflow virtual machine to file
    ```
    vagrant package --base cwl-airflow --output cwl_airflow.box
    ```
21. Test this vm without internet connection

## Additional info
Deprecated repositories:
- https://github.com/Barski-lab/incubator-airflow
- https://github.com/Barski-lab/BioWardrobe2
- https://github.com/SciDAP/scidap


# Queues

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