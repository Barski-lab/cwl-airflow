# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  config.vm.box = "michael_kotliar/cwl-airflow"
  config.vm.box_version = "0.0.2"
  config.vm.box_check_update = false
  config.vm.network "forwarded_port", guest: 8080, host: 8080, host_ip: "127.0.0.1"

  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.memory = 4096
    vb.cpus = 4
  end
end
