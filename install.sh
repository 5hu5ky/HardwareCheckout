#!/bin/bash

#@author: dtechshield 

#This assumes all is installed under /opt/HardwareCheckout

APP_PATH=/opt/hardware
GIT_PATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
DBNAME=chvappdb
DBUNAME=chvapp
DBPASS=$(head -10 /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | sort -r | head -n 1)

echo "Installing required system packages...(if needed)"

echo "Checking for pip3"
if sudo dpkg -l | sudo grep python3-pip 2>&1 > /dev/null; then
	echo "pip3 exists..."
else
	echo "pip3 does not exist"
	sudo apt-get -qq -y update
	sudo apt-get -qq -y install python3-pip
fi

echo "Checking for postgresql"
if sudo dpkg -l | sudo grep postgresql 2>&1 > /dev/null; then
	echo "postpgres exists..."
else
	echo "postgres does not exist"
	sudo apt-get -qq -y update
	sudo apt-get -qq -y install postgresql postgresql-contrib postgresql-server-dev-all
	#/usr/lib/postgresql/10/bin/pg_ctl -D /var/lib/postgresql/10/main -l logfile start
	
fi

echo "Configuring the database..."

if psql -lqt | cut -d \| -f 1 | grep -qw $DBNAME; then
    # database exists
    # $? is 0
    echo "$DBNAME exists.. Leaving it as it is... If you want a fresh DB drop it manually and try again..."
    while true; do
    read -p "Do you want me to continue? (y/N)?" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
  done

else

   #Create Postgresql Pre-reqs
   sudo postgres <<EOF
   psql -c "CREATE USER $DBUNAME WITH PASSWORD '$DBPASS' CREATEDB;"
   createdb -O$DBUNAME -Eutf8 $DBNAME
   echo "Postgres user and database '$1' created."
EOF

fi

# TODO
# echo "Creating web server user"
# sudo useradd $DBUNAME

echo "Creating clone of git repo"
sudo mkdir -p $APP_PATH
# sudo chown $DBUNAME:$DBUNAME $APP_PATH # TODO
# sudo -u $DBUNAME git clone $GIT_PATH $APP_PATH # TODO
git clone $GIT_PATH $APP_PATH

echo "Installing required application packages...(if needed)"

yes | pip3 install virtualenv

pushd $APP_PATH
if [ ! -d "$APP_PATH/venv" ]; then
  # sudo -u $DBUNAME python3 -m virtualenv venv # TODO
  python3 -m virtualenv venv
fi

source venv/bin/activate
yes | pip3 install -r requirements.txt

echo "Writting application config"
cat << EOF > $APP_PATH/HardwareCheckout/config.py
#!/usr/bin/env python3
db_path = 'postgresql+psycopg2://$DBUNAME:$DBPASS@127.0.0.1:5432/$DBNAME'
ssl_config = {
  'certfile':'',
  'keyfile':''
  }
EOF


#Generate run.sh
cat << EOF > $APP_PATH/run.sh
export TORNADO_SECRET_KEY=\$(head -10 /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | sort -r | head -n 1)
python3 -m HardwareCheckout
EOF

chmod a+x $APP_PATH/run.sh

#Turn it into a service
sudo cat << EOF > /etc/systemd/system/HardwareCheckout.service
[Unit]
Description=Hardware Checkout Service
After=network.target

[Service]
User=root
Restart=on-failure
WorkingDirectory=$APP_PATH
ExecStart=$APP_PATH/run.sh

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling Service..."
sudo systemctl enable HardwareCheckout 
sudo systemctl daemon-reload
sudo systemctl start HardwareCheckout


echo "Done..."
