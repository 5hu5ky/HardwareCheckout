#!/usr/bin/env bash

UNAME=villager

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <URL> <Device Name>"
    exit 1
fi

echo "Creating device user $UNAME"
##Creating a user with a home folder remove -m if you do not want a home folder###
sudo adduser --disabled-password --gecos "" $UNAME --shell /bin/bash

###Add villager to dialout group###
sudo usermod -a -G dialout $UNAME

###Generate a strong ssh key###
sudo -u $UNAME ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -C "$UNAME@$HOSTNAME"



SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
apt-get install -y python3-pip
pip3 install -r $SCRIPTPATH/requirements.txt

if [ -f $SCRIPTPATH/device.py.bak ]; then
    mv $SCRIPTPATH/device.py.bak $SCRIPTPATH/device.py
fi
if [ -f $SCRIPTPATH/connected.py.bak ]; then
    mv $SCRIPTPATH/connected.py.bak $SCRIPTPATH/connected.py
fi

sed -i.bak "s|localhost:8080|$1|g" $SCRIPTPATH/device.py
sed -i.bak "s|localhost:5000|$1|g" $SCRIPTPATH/connected.py

sudo install -m 755 -d /opt/hc-client
sudo install -m 755 $SCRIPTPATH/{connected.py,deprovision.sh,device.py,provision.sh} /opt/hc-client
sudo install -m 644 $SCRIPTPATH/{session.target,session@.service} /etc/systemd/system

sudo $SCRIPTPATH/create_config.py $2 6

sudo systemctl daemon-reload
sudo systemctl start session.target
sudo systemctl enable session.target
