import asyncio
try:
    from bleak import BleakScanner, BleakClient
except Exception:
    BleakScanner = None

# 過濾無名的設備
IGNORE_UNKNOW_DEVICE = True
# 過濾非BLELEDDM
IGNORE_NONE_BLELDEDDM_DEVICE = True


class BleManager:
    def __init__(self):
        if BleakScanner is None:
            raise Exception("bleak not install")

    async def discover_devices(self):
        #掃描藍芽設備
        devices = await BleakScanner.discover()
        return self.filter_ble_devices(devices)

    def filter_ble_devices(self, devices):
        # 過濾 BLE 設備
        visible_device = []
        for device in devices:
            if device.name and IGNORE_UNKNOW_DEVICE:
                if "BLEDDM" in device.name and IGNORE_NONE_BLELDEDDM_DEVICE:
                    visible_device.append(device)
        return visible_device
    
    async def connect_device(self, dev_addr): 
        #連線設備
        async with BleakClient(dev_addr) as client:
            if client.is_connected:
                return True
            else:
                return False