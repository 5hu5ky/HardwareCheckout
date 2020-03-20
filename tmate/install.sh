#!/usr/bin/env bash
SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

sudo cp $SCRIPTPATH/session.sh $SCRIPTPATH/session_restart.sh /usr/local/sbin
sudo cp $SCRIPTPATH/session.service /etc/systemd/system/
sudo systemctl daemon-relead
sudo systemctl enable session.service
sudo systemctl start session.service