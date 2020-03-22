#!/bin/bash
set -e
SOCK=/tmp/tmate.sock

tmate -S $SOCK new-session -d
tmate -S $SOCK wait tmate-ready
WEB=tmate -S $SOCK display -p "#{tmate_web}"
WEB_RO=tmate -S $SOCK display -p "#{tmate_web_ro}"
env>/tmp/test_$1
python3 <<EOF
import requests
session = requests.session()
session.post("http://virtual.carhackingvillage.com/login", data={'name':$1,'password':$2})
session.post("http://virtual.carhackingvillage.com/checkin", json={'web':'$WEB','web_ro':'$WEB_RO'})

EOF