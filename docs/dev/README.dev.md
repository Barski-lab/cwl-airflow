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
11. Install cwl-airflow python package following instructions from readme
12. Make sure to set Network / Adapter 1 to NAT for cwl-airflow virtual machine
13. Package cwl-airflow virtual machine to file
    ```
    vagrant package --base cwl-airflow --output cwl_airflow.box
    ```

## Additional info
Deprecated repositories:
- https://github.com/Barski-lab/incubator-airflow
- https://github.com/Barski-lab/BioWardrobe2
- https://github.com/SciDAP/scidap