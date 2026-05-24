"""
list_usb.py - Enumerate every USB device libusb can see.

The bench_tester is hardcoded to look for VID=0x1d50 PID=0x606f (the
"official" candleLight ID). Many SH-C31A units present a different
VID/PID even though Device Manager labels them as gs_usb/candleLight.

Run this and look for your adapter in the list. Unplug it, run again,
plug it back in, run again -- whatever line *appears* is the SH-C31A.

    python list_usb.py
"""
import sys

try:
    import libusb_package
    import usb.core
    import usb.util
except ImportError as e:
    print(f"Missing package: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

backend = libusb_package.get_libusb1_backend()

print("=" * 70)
print("All USB devices visible to libusb_package:")
print("=" * 70)

devices = list(usb.core.find(find_all=True, backend=backend))
if not devices:
    print("\nNO USB DEVICES FOUND AT ALL.")
    print("This means libusb_package is broken or no devices are bound to WinUSB.")
    print("\nMost USB devices on Windows are NOT visible via libusb -- only")
    print("ones whose driver has been replaced with WinUSB (via Zadig) show up.")
    sys.exit(0)

for dev in devices:
    vid = dev.idVendor
    pid = dev.idProduct
    try:
        manuf = usb.util.get_string(dev, dev.iManufacturer) or "?"
    except Exception:
        manuf = "?"
    try:
        prod = usb.util.get_string(dev, dev.iProduct) or "?"
    except Exception:
        prod = "?"
    flag = ""
    # Known candleLight / gs_usb VID:PID pairs
    if (vid, pid) in [
        (0x1d50, 0x606f),  # canonical candleLight
        (0x1d50, 0x606e),
        (0x1d50, 0x6070),
        (0x16d0, 0x0f30),  # CANtact
        (0x1209, 0x2323),  # candleLight clone
        (0xc251, 0x2603),  # some SH-C31A clones
    ]:
        flag = "  <-- looks like a candleLight/gs_usb adapter"
    print(f"  VID=0x{vid:04x}  PID=0x{pid:04x}  {manuf} | {prod}{flag}")

print()
print("=" * 70)
print("Now testing gs_usb.scan() (what bench_tester actually uses):")
print("=" * 70)

# Apply the same monkey-patch bench_tester uses
_orig_find = usb.core.find
def _patched_find(*a, **kw):
    kw.setdefault("backend", backend)
    return _orig_find(*a, **kw)
usb.core.find = _patched_find

try:
    from gs_usb.gs_usb import GsUsb
    found = GsUsb.scan()
    print(f"GsUsb.scan() found {len(found)} device(s)")
    for d in found:
        print(f"  -> bus={d.bus}  address={d.address}")
except ImportError:
    print("gs_usb not installed -- run: pip install gs_usb")
except Exception as e:
    print(f"gs_usb.scan() raised: {e}")
