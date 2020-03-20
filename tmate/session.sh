#!/bin/bash
set -e
SOCK=/tmp/tmate.sock

tmate -S $SOCK new-session -d
tmate -S $SOCK wait tmate-ready
tmate -S $SOCK display -p "#{tmate_web}" > /tmp/web
tmate -S $SOCK display -p "#{tmate_web_ro}" > /tmp/web_ro
