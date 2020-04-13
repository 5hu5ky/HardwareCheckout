#!/bin/bash

set -e

if [ $USE_DOCKER -eq 1 ]
then
    docker stop "$DEVICE_NAME"
    docker rm "$DEVICE_NAME"
else
    tmate -S "$TMATE_SOCK" kill-session
fi
