#!/bin/bash

#@author: dtechshield 

#This assumes all is installed under /opt/HardwareCheckout

GITREPO=https://github.com/linted/HardwareCheckout.git
APP_PATH=/opt/HardwareCheckout
DBNAME=chvappdb
DBUNAME=chvapp
DBPASS=$(head -10 /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | sort -r | head -n 1)

echo "Run this once and you should be set... Make sure to run it as root!"


if [ ! -d "$APP_PATH" ]; then

  while true; do
    read -p "$APP_PATH does not exist - do you want me to clone the repo? (y/N)?" yn
    case $yn in
        [Yy]* ) sudo git clone $GITREPO $APP_PATH; break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
  done
    
fi

echo "Installing required system packages...(if needed)"

if sudo dpkg -l | sudo grep python3-pip 2>&1 > /dev/null; then
	echo "pip3 exists..."
else
	echo "pip3 does not exist; installing..."
	sudo apt-get -qq -y update
	sudo apt-get -qq -y install python3-pip
fi

if sudo dpkg -l | sudo grep postgresql 2>&1 > /dev/null; then
	echo "postpgres exists..."
else
	echo "postgres does not exist; installing..."
	sudo apt-get -qq -y update
	sudo apt-get -qq -y install postgresql postgresql-contrib postgresql-server-dev-all
	#/usr/lib/postgresql/10/bin/pg_ctl -D /var/lib/postgresql/10/main -l logfile start
	
fi

echo "Configuring the database..."
sudo -u postgres psql -c "SELECT datname FROM pg_catalog.pg_database WHERE datname='$DBNAME'" | grep -wq $DBNAME
DB_EXISTS=$?


if [[ "$DB_EXISTS" -eq 0 ]]; then
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
sudo su postgres <<EOF
psql -c "CREATE USER $DBUNAME WITH PASSWORD '$DBPASS' CREATEDB;"
createdb -O$DBUNAME -Eutf8 $DBNAME
echo "Postgres user '$DBUNAME' and database '$DBNAME' created."
EOF

fi


echo "Installing required application packages...(if needed)"

yes | pip3 install virtualenv

cd $APP_PATH
if [ ! -d "$APP_PATH/venv" ]; then
  sudo python3 -m virtualenv venv
fi

source venv/bin/activate
yes | pip3 install -r requirements.txt

deactivate

#Configure Application
sudo cat << EOF > $APP_PATH/HardwareCheckout/config.py
#!/usr/bin/env python3
db_path = 'postgresql+psycopg2://$DBUNAME:$DBPASS@127.0.0.1:5432/$DBNAME'
EOF

TDSK=$(head -10 /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | sort -r | head -n 1)

#Generate run.sh for local runs
sudo cat << EOF > $APP_PATH/run.sh
export TORNADO_SECRET_KEY=$TDSK
source /opt/HardwareCheckout/venv/bin/activate
python3 -m HardwareCheckout
EOF
sudo chmod a+x $APP_PATH/run.sh

#Turn it into a service
sudo cat << EOF > /etc/systemd/system/HardwareCheckout.service
[Unit]
Description=Hardware Checkout Service
After=network.target

[Service]
User=root
Restart=on-failure
Environment=TORNADO_SECRET_KEY=$TDSK
WorkingDirectory=$APP_PATH
ExecStart=$APP_PATH/venv/bin/python3 -m HardwareCheckout

[Install]
WantedBy=multi-user.target


echo "Enabling Service..."
sudo systemctl enable HardwareCheckout 
sudo systemctl daemon-reload
sudo systemctl start HardwareCheckout 


echo "Done..."