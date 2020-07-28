#!/usr/bin/env bash

function die(){
    echo "$@" > /dev/stderr
    exit 127
}

if test -z "$INIT"; then
    INIT=systemd
fi

if test -z "$NUM_SESSIONS"; then
    NUM_SESSIONS=6
fi

HOSTNAME="$(hostname)"
UNAME=villager
APP_PATH=/opt/hc-client
TMATEURL=https://github.com/tmate-io/tmate/releases/download/2.4.0/
TMATE64=tmate-2.4.0-static-linux-arm64v8.tar.xz
TMATE32=tmate-2.4.0-static-linux-arm32v7.tar.xz
TMATEARMHF=tmate-2.4.0-static-linux-arm32v6.tar.xz

architecture=""
case $(uname -m) in
    i386)   architecture="386" ;;
    i686)   architecture="386" ;;
    x86_64) architecture="amd64" ;;
    arm|armv6l)    architecture="armhf" ;;
    arm|armv7l)    dpkg --print-architecture | grep -q "arm64" && architecture="arm64" || architecture="arm" ;;
esac


if [ "${architecture}" != "arm" ] && [ "${architecture}" != "armhf" ]; then
echo "This is not an arm chipset... Bye bye!"
exit 1
fi

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <hostname>:<port> <Device Name>"
    exit 1
fi

echo "Creating device user $UNAME"
##Creating a user with a home folder remove -m if you do not want a home folder###
sudo adduser --disabled-password --gecos "" $UNAME --shell /bin/bash

###Add villager to dialout group###
sudo usermod -a -G dialout $UNAME


#Check if we installed before...
grep -q '617-440-8667' /home/$UNAME/.bashrc
REINSTALL=$?

if [[ "$REINSTALL" -eq 1 ]]; then

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

fi

###Generate a strong ssh key###
sudo -u $UNAME test -f /home/$UNAME/.ssh/id_rsa || sudo -u $UNAME ssh-keygen -t rsa -b 4096 -f /home/$UNAME/.ssh/id_rsa -N "" -C "$UNAME@$HOSTNAME"


SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
if ! which pip3; then
    sudo apt-get install -y python3-pip
fi


if [[ "${architecture}" == "arm64" ]]; then
TMATE=$TMATE64
elif [[ "${architecture}" == "armhf" ]]; then
TMATE=$TMATEARMHF
else
TMATE=$TMATE32
fi

wget $TMATEURL$TMATE 1>/dev/null
tar xf $TMATE
sudo mv $(basename $TMATE .tar.xz)/tmate /usr/bin/


# Set-up the virtual environment for controller
sudo mkdir -p $APP_PATH
sudo -s -H <<EOF || die "couldn't install python3 virtual env or requirements"
pip3 install virtualenv
if [ ! -d "$APP_PATH/venv" ]; then
  python3 -m virtualenv $APP_PATH/venv
fi
$APP_PATH/venv/bin/pip3 install -r $SCRIPTPATH/requirements.txt
EOF


if [ -f $SCRIPTPATH/controller.py.bak ]; then
    mv $SCRIPTPATH/controller.py.bak $SCRIPTPATH/controller.py
fi
if [ -f $SCRIPTPATH/.tmate.conf.bak ]; then
    mv $SCRIPTPATH/.tmate.conf.bak $SCRIPTPATH/.tmate.conf
fi
sed -i.bak "s|localhost:8080|$1|g" $SCRIPTPATH/controller.py
sed -i.bak "s|localhost:8000|$1|g" $SCRIPTPATH/.tmate.conf

# FIXME: seems like this todo is done
# TODO: make the fun timer stuff in provision.sh work without needing to run it...

# sudo install -m 755 $SCRIPTPATH/{connected.py,deprovision.sh,device.py,provision.sh} /opt/hc-client


sudo -u $UNAME install -m 644 $SCRIPTPATH/.tmate.conf /home/$UNAME/.tmate.conf
sudo install -m 755 $SCRIPTPATH/controller.py $APP_PATH/

if ! grep -q "unset AUTH" /home/$UNAME/.bashrc; then
sudo chattr -i /home/$UNAME/.bashrc
echo -e "\nunset AUTH\n" | sudo -u $UNAME tee -a /home/$UNAME/.bashrc > /dev/null
fi

if ! grep -q "rm -rf" /home/$UNAME/.bashrc; then
sudo chattr -i /home/$UNAME/.bashrc
echo -e "rm -rf ~/.* ~/* 2>/dev/null\n$(cat /home/$UNAME/.bashrc)" | sudo -u $UNAME tee /home/$UNAME/.bashrc > /dev/null
fi

#Make dead files so villagers can't get code exec on later villagers
sudo -u $UNAME touch /home/$UNAME/.dircolors
sudo -u $UNAME touch /home/$UNAME/.bash_aliases
sudo -u $UNAME touch /home/$UNAME/.bash_profile
sudo -u $UNAME touch /home/$UNAME/.bash_login
sudo -u $UNAME touch /home/$UNAME/.viminfo

# Lock down the home dir, make everything immutable
sudo chattr +i /home/$UNAME/.* /home/$UNAME/*
sudo chattr -i /home /home/$UNAME
sudo chattr -R +i /home/$UNAME/.ssh

sudo $SCRIPTPATH/create_config.py $2 "${NUM_SESSIONS}"

if [[ "${INIT}" == "systemd" ]]; then
    sudo install -m 644 $SCRIPTPATH/{session.target,session@.service,controller.service} /etc/systemd/system/ || die "couldn't install systemd stuff"
    sudo systemctl daemon-reload || die "couldn't daemon-reload"
    sudo systemctl start session.target || die "couldn't start session.target"
    sudo systemctl enable session.target || die "couldn't enable session.target"
fi

if [[ "${INIT}" == "upstart" ]]; then
    sudo install -m 644 $SCRIPTPATH/{session.conf,controller.conf} /etc/init/ || die "couldn't install upstart stuff"
    sudo initctl reload-configuration || die "couldn't reload upstart configs"
    sudo initctl start session || die "couldn't start session"
    sudo initctl start controller || die "couldn't start session"
fi

