#!/bin/bash

SOCK=/tmp/tmate.sock
tmate -S $SOCK kill-session
/root/session.sh
