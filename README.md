# HardwareCheckout

A simple website which will facilitate physical hardware checkout

## Server Installation

Step 1 - git clone

```
git clone https://github.com/5hu5ky/HardwareCheckout.git
```
 
Step 2 - Install the server... 

```
cd HardwareCheckout
chmod a+x ./install.sh
./install.sh
```


## Operational Notes

### General
The service runs under its own user and virtual environment...

The application is installed as a service and can started and stopped like this:

```
systemctl start HardwareCheckout
systemctl stop HardwareCheckout
```

### Debugging

If you want to debug the application:

```
journalctl -u HardwareCheckout
```

View the entries within the last five minutes:

```
journalctl -u HardwareCheckout --since=-5m
```

View the last 25 log entries:

```
journalctl -u HardwareCheckout -n 25
```

Tail the log:

```
journalctl -u HardwareCheckout -f
```


If you want to run it as a foreground service:

```
systemctl stop HardwareCheckout
su chvapp
cd /opt/HardwareCheckout
./run.sh
```

### Application Access

#### No SSL Setup

Once the install is done the server will come up on - `http://127.0.0.1:8080`

#### SSL setup

You can quickly get going using Let's Encrypt; copy this into certbot-install.sh:

```
#!/bin/bash
sudo apt-get update
sudo apt-get install software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository ppa:certbot/certbot
sudo apt-get update

sudo apt-get install certbot python-certbot-apache
```

run `./certbot-install.sh`

This will install the certbot, once installed (if you are running apache):

`sudo certbot --apache`

Once installed configure the installation with the SSL key and cert by editing `/opt/HardwareCheckout/HardwareCheckout/config.py`

Do not forget to switch users - `su chvapp`

```
...
ssl_config = {
  "certfile": "/etc/letsencrypt/live/<domain.name.com>/fullchain.pem",
  "keyfile": "/etc/letsencrypt/live/<domain.name.com>/privkey.pem",

  }

```

and

`systemctl restart HardwareCheckout` - you will need to be root privileged for this...

The server will come up on `https://127.0.0.1` 

## Operating Server Functions [High-Level]

### Add admin
- `./addAdmin.py <username> <password>`

### Add device type
- `./addDeviceType.py <type name>`

### Add device
- `./addDevice.py <device name> <password> <device type>`

### Hardware setup
- `./tmate/install.sh <hostname or ip of server>`
