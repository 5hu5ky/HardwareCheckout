#!/bin/bash
set -e
SOCK=/tmp/tmate$1.sock

tmate -S $SOCK new-session -d
tmate -S $SOCK wait tmate-ready
WEB=$(tmate -S $SOCK display -p "#{tmate_web}"),$(tmate -S $SOCK display -p "#{tmate_ssh}")
WEB_RO=$(tmate -S $SOCK display -p "#{tmate_web_ro}")

python3 <<EOF
import requests
session = requests.session()
session.post("http://virtual.carhackingvillage.com/login", data={'name':'device$1','password':'ASubsfas2341'})
session.post("http://virtual.carhackingvillage.com/checkin", json={'web':'$WEB','web_ro':'$WEB_RO'})

EOF