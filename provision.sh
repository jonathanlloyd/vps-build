#!/bin/bash

# Default variables
ADMIN_PASSWORD="password"
FQDN="dev.box"
SSH_PUB=""
GIB_CONFIG="
{
    \"consumer_key\": \"\",
    \"consumer_secret\": \"\",
    \"access_key\": \"\",
    \"access_secret\": \"\"
}
"


# Load variable overrides from .env
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source /vagrant/.env


# Basic Box Config
## Update apt repos
apt-get update

## Change hostname
hostnamectl set-hostname bombe
(echo "127.0.0.1	bombe"; cat /etc/hosts) > /tmp/hosts; mv /tmp/hosts /etc/hosts

## Create admin user
adduser jonathan --gecos "Jonathan Lloyd,N/A,N/A,N/A" --disabled-password
echo "jonathan:$ADMIN_PASSWORD" | chpasswd
usermod -aG sudo jonathan

### Set up ssh key
mkdir /home/jonathan/.ssh
chmod 700 /home/jonathan/.ssh
echo "$SSH_PUB" > /home/jonathan/.ssh/authorized_keys
chmod 600 /home/jonathan/.ssh/authorized_keys
chown -R jonathan /home/jonathan/.ssh
### Disable password login
sed -i "s/^.*PasswordAuthentication.*$/PasswordAuthentication No/g" /etc/ssh/sshd_config

## Firewall
### Defaults
ufw default deny incoming
ufw default allow outgoing
### Allow ssh traffic
ufw allow OpenSSH
### Allow http traffic
ufw allow www
## Enable firewall
ufw enable


# Make apps dir
mkdir /home/jonathan/apps


# Install GameIdeaBot
## Install Python2.7
apt install -y python

## Install pip
apt install -y python-pip

## Download GameIdeaBot
pushd /home/jonathan/apps
git clone https://github.com/turingincomplete/gameideabot

## Install requirements
pip install -r gameideabot/requirements.txt

## Add GameIdeaBot config
echo "$GIB_CONFIG" > ./gameideabot/gameideabot/config.json

## Add to cron
(crontab -l; echo "0 * * * * /home/jonathan/apps/gameideabot/run.sh") |crontab -u jonathan -

## Clean up
popd


# Install Dokku
## install prerequisites
apt-get install -qq -y apt-transport-https

## install docker
wget -nv -O - https://get.docker.com/ | sh

## Config
echo "dokku dokku/web_config boolean false" | debconf-set-selections
echo "dokku dokku/vhost_enable boolean true" | debconf-set-selections
echo "dokku dokku/hostname string $FQDN" | debconf-set-selections
echo "dokku dokku/key_file string /home/jonathan/.ssh/authorized_keys" | debconf-set-selections

## install dokku
wget -nv -O - https://packagecloud.io/gpg.key | apt-key add -
echo "deb https://packagecloud.io/dokku/dokku/ubuntu/ trusty main" | sudo tee /etc/apt/sources.list.d/dokku.list
apt-get update -qq > /dev/null
apt-get install -qq -y dokku
dokku plugin:install-dependencies --core
