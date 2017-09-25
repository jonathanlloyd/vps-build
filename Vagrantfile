# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Base Image
  config.vm.box = "ubuntu/xenial64"
  config.vm.box_check_update = false


  # Networking
  config.vm.network "private_network", ip: "192.168.33.10"

  # Disable shared folders
  #config.vm.synced_folder ".", "/vagrant", disabled: true

  # Tweak virtualbox
  config.vm.provider :virtualbox do |vb|
      # Speed up machine startup by using linked clones
      vb.linked_clone = true
  end

  # Provisioning
  config.vm.provision "shell", path: "provision.sh"
end
