# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Base Image
  config.vm.box = "bento/ubuntu-22.04"
  config.vm.box_check_update = false

  # Networking
  config.vm.network "private_network", ip: "192.168.56.101"

  # Tweak virtualbox
  config.vm.provider :virtualbox do |vb|
      # Speed up machine startup by using linked clones
      vb.linked_clone = true
  end

  # Provisioning
  # config.vm.provision "shell", path: "provision.sh"
end
