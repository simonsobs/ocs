"""
Script to get the nodes to serial devices that are plugged in.
If you are using a new device (like the Lakeshore372) you must add the vendorID and productID to the device_ids dict.
"""


import subprocess
import os.path as path
import re

device_ids = {
    (0x1fb9, 0x0205): "Lakeshore240"
}

def getUSBNodes():
    dev_path = "/sys/bus/usb-serial/devices/"

    p = re.compile('PRODUCT=(?P<vendID>\w+)/(?P<prodID>\w+)')

    nodes = []
    for node in subprocess.check_output(["ls", dev_path]).decode()[:-1].split('\n'):
        u_file = path.join(dev_path, node, "../uevent")
        match = p.search(subprocess.check_output(['cat', u_file]).decode())
        info = match.groupdict()

        key = (int(info['vendID'], 16), int(info['prodID'], 16))
        product_name = device_ids.get(key)

        if product_name is not None:
            nodes.append((node, product_name))

    return nodes


