#!/bin/bash

SOCK=/tmp/tmate$1.sock
tmate -S $SOCK kill-session
/usr/local/sbin/session.sh $1
