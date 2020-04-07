# HardwareCheckout
A simple website which will facilitate physical hardware checkout

# Server

## Dev setup
- Optional - set up virtual env
    ```
    python3 -m virtualenv venv
    source venv/bin/activate
    ```
- `pip3 -r requirements.txt`
- `./run.sh`

## Add admin
- `./addAdmin.py <username> <password>`

## Add device type
- `./addDeviceType.py <type name>`

## Add device
- `./addDevice.py <device name> <password> <device type>`
