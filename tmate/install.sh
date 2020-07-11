#!/usr/bin/env bash

UNAME=villager
APP_PATH=/opt/hc-client

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <URL> <Device Name>"
    exit 1
fi

echo "Creating device user $UNAME"
##Creating a user with a home folder remove -m if you do not want a home folder###
sudo adduser --disabled-password --gecos "" $UNAME --shell /bin/bash

###Add villager to dialout group###
sudo usermod -a -G dialout $UNAME

cat <<"EOF" | sudo -u $UNAME tee -a /home/$UNAME/.bashrc > /dev/null


echo "  


        
                                      _.-=\"\"_-         _
                                 _.-=\"  \"_-           | ||\"\"\"\"\"\"\"-\"--_______     __..
                     ___.===\"\"\"\"-.______-,,,,,,,,,,,,,-\\''----\" \"\"\"\"\"      \"\"\"\"\" \"_ 
              __.--\"\"     __        ,'                   o \\           __        [_|
         __-\"\"=======.--\"\"  \"\"--.=================================.--\"\"  \"\"--.=======:
        ]       [w] : /        \ : |== Welcome to the ======|    : /        \ :  [w] :
        V___________:|          |: |= Car Hacking Village ==|    :|          |:   _-
         V__________: \        / :_|=======================/_____: \        / :__-
         -----------'  \"-____-\"  --------------------------------'  \"-____-\"



        Welcome to the Car Hacking Village.  This is SUPER BETA!
        If you need help find us on the discord or slack or by phone at 617-440-8667
	Please wait while we set things up for you to hack...
	
	**** PLEASE NOTE - TERMINTATING BASH WILL TERMINATE YOUR SESSION! DON'T CRY LATER!!!! ****
"
EOF


###Generate a strong ssh key###
sudo -u $UNAME ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -C "$UNAME@$HOSTNAME"



SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
apt-get install -y python3-pip

# TODO install tmate 2.4.0 for the correct arch not just arm64
#wget 'https://github.com/tmate-io/tmate/releases/download/2.4.0/tmate-2.4.0-static-linux-arm64v8.tar.xz' 1>/dev/null
#tar xf tmate-2.4.0-static-linux-arm64v8.tar.xz
#mv tmate-2.4.0-static-linux-arm64v8/tmate /usr/bin
# 32 bit version
wget 'https://github.com/tmate-io/tmate/releases/download/2.4.0/tmate-2.4.0-static-linux-arm32v7.tar.xz' 1>/dev/null
tar xf tmate-2.4.0-static-linux-arm32v7.tar.xz
mv tmate-2.4.0-static-linux-arm32v7/tmate /usr/bin

# Set-up the virtual environment as the villager user?
sudo -u $UNAME -s -H <<EOF
pip3 install virtualenv
if [ ! -d "$APP_PATH/venv" ]; then
  python3 -m virtualenv $APP_PATH/venv
fi
source $APP_PATH/venv/bin/activate
pip3 install -r $SCRIPTPATH/requirements.txt
deactivate
EOF


if [ -f $SCRIPTPATH/controller.py.bak ]; then
    mv $SCRIPTPATH/controller.py.bak $SCRIPTPATH/controller.py
fi
if [ -f $SCRIPTPATH/.tmate.conf.bak ]; then
    mv $SCRIPTPATH/.tmate.conf.bak $SCRIPTPATH/.tmate.conf
fi
sed -i.bak "s|localhost:8080|$1|g" $SCRIPTPATH/controller.py
sed -i.bak "s|localhost:8000|$1|g" $SCRIPTPATH/.tmate.conf

# TODO: make the fun timer stuff in provision.sh work without needing to run it...

# sudo install -m 755 -d /opt/hc-client
# sudo install -m 755 $SCRIPTPATH/{connected.py,deprovision.sh,device.py,provision.sh} /opt/hc-client


sudo install -m 755 $SCRIPTPATH/controller.py $APP_PATH
sudo install -m 644 $SCRIPTPATH/.tmate.conf /home/$UNAME/.tmate.conf
sudo install -m 644 $SCRIPTPATH/{session.target,session@.service,controller.service} /etc/systemd/system

#Make .bashrc immutable
echo -e "\nunset AUTH\n" >> /home/$UNAME/.bashrc
sudo chown root:root /home/$UNAME/.bashrc
sudo chmod 755 /home/$UNAME/.bashrc
chattr +i /home/$UNAME/.bashrc

sudo $SCRIPTPATH/create_config.py $2 6

sudo systemctl daemon-reload
sudo systemctl start session.target
sudo systemctl enable session.target
