#!/usr/bin/env bash
SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
apt-get install -y python3-pip
pip3 install requests
sudo cp $SCRIPTPATH/session.sh $SCRIPTPATH/session_restart.sh /usr/local/sbin
sudo cp $SCRIPTPATH/session.target /etc/systemd/system/
sudo cp $SCRIPTPATH/session@.service /lib/systemd/system/
sudo cp $SCRIPTPATH/autologout.sh /etc/profile.d/autologout.sh
sudo systemctl daemon-reload
sudo systemctl start session.target
sudo systemctl enable session.target