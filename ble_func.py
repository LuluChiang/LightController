import asyncio
try:
    from bleak import BleakScanner
except Exception:
    BleakScanner = None

IGNORE_UNKNOW_DEVICE = True
IGNORE_NONE_BLELDEDDM_DEVICE = True

async def discover_devices():
    #掃描藍芽設備
    if BleakScanner is None:
        raise Exception("bleak 未安裝")
    
    devices = await BleakScanner.discover()
    return filter_ble_devices(devices)

def filter_ble_devices(devices):
    # 過濾 BLE 設備
    visible_device = []
    for device in devices:
        if device.name and IGNORE_UNKNOW_DEVICE:
            if "BLEDDM" in device.name and IGNORE_NONE_BLELDEDDM_DEVICE:
                visible_device.append(device)
    return visible_device