|Build Status| # cwl-airflow

About
~~~~~

Python package to extend **`Apache-Airflow 1.8.2`_** functionality with
**`CWL v1.0`_** support.

Installation
~~~~~~~~~~~~

1. Get the latest release of ``cwl-airflow``
   ``sh    $ pip install cwl-airflow``

   .. raw:: html

      <details>

   Details & Requirements

   Automatically installs:

   -  Apache-Airflow v1.8.2

      -  cwltool 1.0.20180116213856

      Requirements:

      -  Ubuntu 16.04.3

         -  python 2.7.12
         -  pip

            ::

                sudo apt install python-pip
                pip install --upgrade pip

         -  setuptools

            ::

                pip install setuptools

         -  `docker`_

            ::

                sudo apt-get update
                sudo apt-get install apt-transport-https ca-certificates curl software-properties-common
                curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
                sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
                sudo apt-get update
                sudo apt-get install docker-ce
                sudo groupadd docker
                sudo usermod -aG docker $USER

            Log out and log back in so that your group membership is
            re-evaluated.
         -  libmysqlclient-dev

            .. code:: bash

                sudo apt-get install libmysqlclient-dev

         -  nodejs

            ::

                sudo apt-get install nodejs

            .. raw:: html

               </details>

Configuration
~~~~~~~~~~~~~

1. If you had **`Apache-Airflow v1.8.2`_** already installed and
   configured, you may skip this step ``sh  $ airflow initdb``

   .. raw:: html

      <details>

   Details

   -  creates ``$AIRFLOW_HOME`` folder (if not set ``~/airflow`` is
      used)
   -  creates default Airflow configuration file ``airflow.cfg`` in the
      ``$AIRFLOW_HOME`` folder
   -  initializes Airflow database

   .. raw:: html

      </details>

2. Initialize ``cwl-airflow`` with the following command
   ``sh  $ cwl-airflow init``

   .. raw:: html

      <details>

   Details

   -  updates ``airflow.cfg`` file in your ``$AIRFLOW_HOME`` folder with
      the default parameters for running CWL workflow descriptor files
   -  creates default folders for CWL descriptor and JSON/YAML input
      parameters files based on ``cwl`` section from ``airflow.cfg``
      file
   -  creates ``cwl_airflow`` folder in the directory set as
      ``dags_folder`` parameter in ``airflow.cfg`` file, copies there
      ``cwl_airflow`` Python package for generating DAG’s from CWL files

   .. raw:: html

      </details>

Running
~~~~~~~

Batch mode
^^^^^^^^^^

1. Put your CWL descriptor files with all of the nes

.. _Apache-Airflow 1.8.2: https://github.com/apache/incubator-airflow
.. _CWL v1.0: http://www.commonwl.org/v1.0/
.. _docker: https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/
.. _Apache-Airflow v1.8.2: https://github.com/apache/incubator-airflow

.. |Build Status| image:: https://travis-ci.org/Barski-lab/cwl-airflow.svg?branch=master
   :target: https://travis-ci.org/Barski-lab/cwl-airflow