#!/bin/bash


# Load environment variables from .env
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source /vagrant/.env

#
## Basic Box Config
### Update apt repos
#apt-get update
#
### Change hostname
#hostnamectl set-hostname bombe
#
### Create admin user
#adduser turing --gecos "Alan Turing,N/A,N/A,N/A" --disabled-password
#echo "turing:$ADMIN_PASSWORD" | chpasswd
#usermod -aG sudo turing
#### Set up ssh key
#mkdir /home/turing/.ssh
#chmod 700 /home/turing/.ssh
#echo "$SSH_PUB" > /home/turing/.ssh/authorized_keys
#chmod 600 /home/turing/.ssh/authorized_keys
#chown -R turing /home/turing/.ssh
#### Allow ssh traffic
#ufw allow OpenSSH
#### Disable password login
#sed -i "s/^.*PasswordAuthentication.*$/PasswordAuthentication No/g" /etc/ssh/sshd_config
##systemctl reload sshd
#
### Enable firewall
#ufw enable
#
#
## Install nginx
#apt install -y nginx
#ufw allow 'Nginx HTTP'
#
# Install MySQL
echo "mysql-server-5.7 mysql-server/root_password password root" | sudo debconf-set-selections
echo "mysql-server-5.7 mysql-server/root_password_again password root" | sudo debconf-set-selections
apt install -y mysql-server-5.7


# Install Python 3
