#!/usr/bin/env bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <URL>"
fi

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
apt-get install -y python3-pip
pip3 install -r $SCRIPTPATH/requirements.txt

sed -i.bak "s|localhost:5000|$1|g" $SCRIPTPATH/device.py
sed -i.bak "s|localhost:5000|$1|g" $SCRIPTPATH/connected.py

sudo install -m 755 -d /opt/hc-client
sudo install -m 755 $SCRIPTPATH/{connected.py,deprovision.sh,device.py,provision.sh} /opt/hc-client
sudo install -m 644 $SCRIPTPATH/{session.target,session@.service} /etc/systemd/system

sudo systemctl daemon-reload
sudo systemctl start session.target
sudo systemctl enable session.target
