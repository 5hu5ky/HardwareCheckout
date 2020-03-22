#!/bin/bash
set -e
SOCK=/tmp/tmate$1.sock

env -i tmate -S $SOCK new-session -d
tmate -S $SOCK wait tmate-ready
WEB=tmate -S $SOCK display -p "#{tmate_web}"
WEB_RO=tmate -S $SOCK display -p "#{tmate_web_ro}"

USERNAME_VAR=User$1
PASSWORD_VAR=Password$2

python3 <<EOF
import requests
session = requests.session()
session.post("http://virtual.carhackingvillage.com/login", data={'name':${!USERNAME_VAR},'password':${!PASSWORD_VAR}})
session.post("http://virtual.carhackingvillage.com/checkin", json={'web':'$WEB','web_ro':'$WEB_RO'})

EOF