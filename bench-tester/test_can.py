import libusb_package
import usb.core

backend = libusb_package.get_libusb1_backend()

_orig_find = usb.core.find
def _patched_find(*a, **kw):
    kw.setdefault("backend", backend)
    return _orig_find(*a, **kw)
usb.core.find = _patched_find

from gs_usb.gs_usb import GsUsb
from gs_usb.gs_usb_frame import GsUsbFrame

devs = GsUsb.scan()
print(f"Found {len(devs)} devices")
if devs:
    dev = devs[0]
    dev.set_bitrate(500000)
    dev.start()
    print("CAN bus started!")
