# HardwareCheckout
A simple website which will facilitate physical hardware checkout

# Server

Initial server set-up is done via install.sh - run that first... It does almost everything for you, but cook. Run it as root.

The application is installed as a service and can be interacted like this:

```
service HardwareCheckout start
service HardwareCheckout stop
```

The service runs in its own virtual environment...

# Operating Server Functions [High-Level]

## Add admin
- `./addAdmin.py <username> <password>`

## Add device type
- `./addDeviceType.py <type name>`

## Add device
- `./addDevice.py <device name> <password> <device type>`

# Hardware setup
- `./tmate/install.sh <hostname or ip of server>`

