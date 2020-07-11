#!/usr/bin/env bash

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <URL> <Device Name>"
    exit 1
fi

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
apt-get install -y python3-pip

# TODO install tmate 2.4.0 for the correct arch not just arm64
wget 'https://github.com/tmate-io/tmate/releases/download/2.4.0/tmate-2.4.0-static-linux-arm64v8.tar.xz' 1>/dev.null
tar xf tmate-2.4.0-static-linux-arm64v8.tar.xz
mv tmate-2.4.0-static-linux-arm64v8/tmate /usr/bin

# TODO virtualenv?

pip3 install -r $SCRIPTPATH/requirements.txt

if [ -f $SCRIPTPATH/controller.py.bak ]; then
    mv $SCRIPTPATH/controller.py.bak $SCRIPTPATH/controller.py
fi
if [ -f $SCRIPTPATH/.tmate.conf.bak ]; then
    mv $SCRIPTPATH/.tmate.conf.bak $SCRIPTPATH/.tmate.conf
fi
sed -i.bak "s|localhost:8080|$1|g" $SCRIPTPATH/controller.py
sed -i.bak "s|localhost:8080|$1|g" $SCRIPTPATH/.tmate.conf

# TODO: make the fun timer stuff in provision.sh work without needing to run it...

# sudo install -m 755 -d /opt/hc-client
# sudo install -m 755 $SCRIPTPATH/{connected.py,deprovision.sh,device.py,provision.sh} /opt/hc-client

sudo install -m 755 $SCRIPTPATH/controller.py /opt/hc-client
sudo install -m 644 $SCRIPTPATH/.tmate.conf /home/villager/.tmate.conf
sudo install -m 644 $SCRIPTPATH/{session.target,session@.service,controller.service} /etc/systemd/system

echo -e "\nunset AUTH\n" >> /home/villager/.bashrc
sudo chown root:root /home/villager/.bashrc
sudo chmod 755 /home/villager/.bashrc
sudo chattr +i /home/villager/.bashrc # TODO: Does this actually gives us added security or am I being pedantic?

sudo $SCRIPTPATH/create_config.py $2 6

sudo systemctl daemon-reload
sudo systemctl start session.target
sudo systemctl enable session.target
