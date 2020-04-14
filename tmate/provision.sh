#!/bin/bash

set -e
set -x

cat > "$DATA_DIR/time-remaining.sh" <<EOF
#!/bin/bash

expiration_time="\`cat $EXPIRATION_TIMESTAMP\`"
current_time="\`date +%s\`"

time_remaining="\$((expiration_time - current_time))"

if [ "\$time_remaining" -gt 0 ]
then
        seconds="\`printf %02d \$((time_remaining % 60))\`"
        minutes="\`printf %02d \$((time_remaining / 60))\`"
        echo "Time remaining: \$minutes:\$seconds"
else
        echo "Time remaining: 00:00"
fi
EOF

chmod a+x "$DATA_DIR/time-remaining.sh"

if [ "$USE_DOCKER" -eq 1 ]
then
    docker run -it -d --name="$DEVICE_NAME" \
           -v "$DATA_DIR:$DATA_DIR" \
           -v "$INSTALL_DIR/connected.py:$INSTALL_DIR/connected.py" \
           device_template bash
    ext() {
        docker exec "$DEVICE_NAME" "$@"
    }
else
    ext() {
        "$@"
    }
fi

ext tmate -S "$TMATE_SOCK" new-session -d
ext tmate -S "$TMATE_SOCK" wait tmate-ready
ext tmate -S "$TMATE_SOCK" set-hook -g mate-joined "run-shell \"$INSTALL_DIR/connected.py $DEVICE_NAME\""
ext tmate -S "$TMATE_SOCK" set -g status-right "#($DATA_DIR/time-remaining.sh)"
ext tmate -S "$TMATE_SOCK" set -g status-interval 1
SSH=$(ext tmate -S "$TMATE_SOCK" display -p "#{tmate_ssh}")
WEB=$(ext tmate -S "$TMATE_SOCK" display -p "#{tmate_web}")
WEB_RO=$(ext tmate -S "$TMATE_SOCK" display -p "#{tmate_web_ro}")

echo "ssh = $SSH" >> "$CONFIG_FILE"
echo "web = $WEB" >> "$CONFIG_FILE"
echo "web_ro = $WEB_RO" >> "$CONFIG_FILE"
