#!/bin/bash
set -e
SOCK=/tmp/tmate$1.sock

tmate -S $SOCK new-session -d
tmate -S $SOCK wait tmate-ready
SSH=$(tmate -S $SOCK display -p "#{tmate_ssh}")
WEB=$(tmate -S $SOCK display -p "#{tmate_web}")
WEB_RO=$(tmate -S $SOCK display -p "#{tmate_web_ro}")

python3 <<EOF
import requests
session = requests.session()
session.post("http://localhost:5000/login", data={'name':'device$1','password':'ASubsfas2341'})
session.post("http://localhost:5000/checkin", json={'web':'$WEB','web_ro':'$WEB_RO','ssh':'$SSH'})

EOF