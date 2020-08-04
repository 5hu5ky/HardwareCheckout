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

if test -z "$CTF_MODE"; then
    CTF_MODE="$(which true)"
fi

UNAMES=""
for i in $(seq ${NUM_SESSIONS}); do
    UNAMES="${UNAMES} villager-device$i "
done

HOSTNAME="$(hostname)"
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

prep_user() {
    UNAME="$1"

    sudo adduser --disabled-password --gecos "" $UNAME --shell /bin/bash
    sudo usermod -a -G dialout $UNAME

    if grep -vq '617-440-8667' /home/$UNAME/.bashrc; then
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

    sudo -u $UNAME install -m 644 $SCRIPTPATH/.tmate.conf /home/$UNAME/.tmate.conf

    if ! grep -q "unset AUTH" /home/$UNAME/.bashrc; then
    sudo chattr -i /home/$UNAME/.bashrc
    echo -e "\nunset AUTH\n" | sudo -u $UNAME tee -a /home/$UNAME/.bashrc > /dev/null
    fi

    if ${CTF_MODE} && ! grep -q "rm -rf" /home/$UNAME/.bashrc; then
        sudo chattr -i /home/$UNAME/.bashrc
        echo -e "rm -rf ~/.* ~/* 2>/dev/null\n$(cat /home/$UNAME/.bashrc)" | sudo -u $UNAME tee /home/$UNAME/.bashrc > /dev/null

	if grep -qv "CTF" /home/$UNAME/.bashrc; then
            cat <<"EOF" | sudo -u $UNAME tee -a /home/$UNAME/.bashrc > /dev/null
echo "
    This is a CTF system.
        * The home will be cleared on exit.
        * You can persist in /tmp, but: 1) anyone can read it if they know the path 2) you cannot list files in /tmp 3) /tmp won't persist across system reboots. Save you important files elsewhere.
        * You cannot keep daemons or background jobs running after exit
        * There are no flags on this system, there is nothing to gain by trying priv esc here; except a kick.
"
EOF
	fi
    fi

    #Make both interactive and non-interactive shells use the same init in .bashrc prepared above
    echo "source /home/$UNAME/.bashrc" | sudo -u $UNAME tee /home/$UNAME/.bash_profile > /dev/null

    #Make dead files so villagers can't get code exec on later villagers
    sudo -u $UNAME touch /home/$UNAME/.dircolors
    sudo -u $UNAME touch /home/$UNAME/.bash_aliases
    sudo -u $UNAME touch /home/$UNAME/.bash_login
    sudo -u $UNAME touch /home/$UNAME/.viminfo

    # Lock down the home dir, make everything immutable
    sudo chattr +i /home/$UNAME/.* /home/$UNAME/*
    sudo chattr -i /home /home/$UNAME
    sudo chattr -R +i /home/$UNAME/.ssh

}

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
if [ -f $SCRIPTPATH/controller.py.bak ]; then
    mv $SCRIPTPATH/controller.py.bak $SCRIPTPATH/controller.py
fi
sed -i.bak "s|localhost:8080|$1|g" $SCRIPTPATH/controller.py
if [ -f $SCRIPTPATH/.tmate.conf.bak ]; then
    mv $SCRIPTPATH/.tmate.conf.bak $SCRIPTPATH/.tmate.conf
fi
sed -i.bak "s|localhost:8000|$1|g" $SCRIPTPATH/.tmate.conf

for name in $UNAMES; do
    prep_user $name
done

if ${CTF_MODE}; then
    echo "Installing for CTF: setting /tmp to 0753"
    sudo chmod 753 /tmp 
fi

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

sudo $SCRIPTPATH/create_config.py $2 "${NUM_SESSIONS}"
sudo install -m 755 $SCRIPTPATH/controller.py $APP_PATH/

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

