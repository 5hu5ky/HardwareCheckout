#!/usr/bin/env bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <URL>"
fi

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
apt-get install -y python3-pip
pip3 install requests

if [ -f $SCRIPTPATH/session.sh.bak ]; then
    mv $SCRIPTPATH/session.sh.bak $SCRIPTPATH/session.sh
fi

sed -i.bak "s|localhost:5000|$1|g" $SCRIPTPATH/session.sh

sudo cp $SCRIPTPATH/{session.sh,session_restart.sh} /usr/local/sbin
sudo cp $SCRIPTPATH/session.target /etc/systemd/system/
sudo cp $SCRIPTPATH/session@.service /lib/systemd/system/
sudo cp $SCRIPTPATH/autologout.sh /etc/profile.d/autologout.sh
sudo systemctl daemon-reload
sudo systemctl start session.target
sudo systemctl enable session.target