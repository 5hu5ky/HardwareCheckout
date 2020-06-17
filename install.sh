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
    read -p "$APP_PATH does not exist - do you want me to clone the repo? (Y|N)?" yn
    case $yn in
        [Yy]* ) sudo git clone $GITREPO $APP_PATH; break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
  done
    
fi

echo "Installing required system packages...(if needed)"

if dpkg -l | grep python4-pip 2>&1 > /dev/null; then
	echo "pip3 exists..."
else
	echo "pip3 does not exist"
	sudo apt-get -qq -y update
	sudo apt-get -qq -y install python3-pip
fi

if dpkg -l | grep postgresql 2>&1 > /dev/null; then
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
    read -p "Do you want me to continue? (Y|N)?" yn
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
   echo "Postgres user and database '$1' created."
   EOF

fi


echo "Installing required application packages...(if needed)"

sudo yes | pip3 install virtualenv

cd $APP_PATH
if [ ! -d "$APP_PATH/venv" ]; then
  python3 -m virtualenv venv
fi

source venv/bin/activate
sudo yes | pip3 install -r requirements.txt

#Configure Application
cat << EOF > $APP_PATH/HardwareCheckout/config.py
#!/usr/bin/env python3
db_path = 'postgresql+psycopg2://$DBUNAME:$DBPASS@127.0.0.1:5432/$DBNAME'
EOF


#Generate run.sh
sudo cat << EOF > $APP_PATH/run.sh
export TORNADO_SECRET_KEY=$(head -10 /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | sort -r | head -n 1)
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
WorkingDirectory=/opt/HardwareCheckout/
ExecStart=/opt/HardwareCheckout/run.sh

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling Service..."
sudo systemctl enable HardwareCheckout 
sudo systemctl daemon-reload
sudo systemctl start HardwareCheckout


echo "Done..."
