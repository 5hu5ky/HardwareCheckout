# HardwareCheckout

A simple website which will facilitate physical hardware checkout

## Server Installation

Step 1 - git clone

```
git clone https://github.com/linted/HardwareCheckout.git
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

Additional verbosity from the application can be had by running with the `--logging=debug` argument.

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

This is not a supported configuration; but no server-side setup is needed.

On all clients, you will need to:
* edit `controller.py` to use `ws://` instead of `wss://`
* edit `.tmate.conf` to use `http://` instead of `https://`

#### SSL setup

This is the supported configuration; no changes to any clients are needed; but some setup of certs server-side is.

You can quickly get going using Let's Encrypt; copy this into certbot-install.sh:

```
#!/bin/bash
sudo apt-get update
sudo apt-get install software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository ppa:certbot/certbot
sudo apt-get update

sudo apt-get install certbot 
```

run `./certbot-install.sh`

This will install the certbot, once installed (if you are running apache as a proxy):

`sudo certbot --apache`

If running stand-alone:
`sudo certbot certonly --standalone --preferred-challenges http -d example.com -d www.example.com`

the certificates and key should be saved to `/etc/letsencrypt/live/example.com/fullchain.pem` and `/etc/letsencrypt/live/example.com/privkey.pem` respectively. 

Once installed configure the installation with the SSL key and cert by editing `/opt/HardwareCheckout/HardwareCheckout/config.py`

Do not forget to switch users for editing - `su chvapp`

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
- `./addAdmin.py -u <username> -p <password>`

### Add device type
- `./addDeviceType.py -t <type name>`

### Add device
- Add multiple devices:
`./addDevice.py -i <path/to/inifile> -t <devicetype>`

- Add a single device:
`./addDevice.py -u <devicename> -p <password> -t <devicetype>`

### Remove device
- `./rmDevice.py -d <device name>`

note: you will need to do this for each of the devices created for each session and also the controller. e.g. you will probably need to do

```
./rmDevice.py -d myrpi-device0
./rmDevice.py -d myrpi-device1
./rmDevice.py -d myrpi-device2
./rmDevice.py -d myrpi-device3
./rmDevice.py -d myrpi-device4
./rmDevice.py -d myrpi-device5
./rmDevice.py -d myrpi-controller
```

### Add Twitch stream (on the server side)
- `./addTwitchStream.py -n <streamname>`

### RemoveTwitch stream (on the server side)
- `./rmTwitchStream.py -n <streamname>`


## Hardware Setup (Raspberry Pi)
Clone the repo on to your Rasberry Pi; under the tmate folder look for the `install.sh`
- `./tmate/install.sh <hostname or ip of server>[:<port>] <name of this device>` (a `<port>` can be specified if the server uses a non-standard port)

There are some environment variables you can specify to change the install: `INIT`, `NUM_SESSIONS`, `CTF_MODE`

* `NUM_SESSIONS` default ***6***; specify how many concurrent tmate sessions to support on this device.
* `CTF_MODE` default `true`; specify `false` to disable CTF features such as clearing homedir on exit.
* `INIT` default `systemd`; specify `upstart` for an alternate init system.
