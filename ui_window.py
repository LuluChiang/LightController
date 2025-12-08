import tkinter as tk
from tkinter import ttk
import threading
import asyncio
from ble_func import BleManager

# CONFIG
FONT_CH = "微軟正黑體"
FONT_EN = "Calibri"
FONT_SIZE = 14

class MainWindow:
    def __init__(self):
        # 建立主視窗
        self.mainWindow = tk.Tk()
        self.mainWindow.title("Light Controller")
        self.mainWindow.geometry("1240x640+500+200")    
        self.mainWindow.resizable(False, False)

        self.status_var = tk.StringVar(value="狀態: 未掃描")
        self.deviced_light = []
        self.connected_light={}
        self._setup_ui()
        self.mainWindow.mainloop()

    def _setup_ui(self):
        # 建立設定清單視窗frame
        status_label = ttk.Label(self.mainWindow, textvariable=self.status_var, font=(FONT_CH, FONT_SIZE))
        status_label.pack(anchor="w", padx=10, pady=5)

        btn_frame = ttk.Frame(self.mainWindow, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Style().configure("TLabelframe.Label", font=(FONT_CH, FONT_SIZE, "bold"))
        device_frame = ttk.LabelFrame(self.mainWindow, text="設備列表(點擊連線)", padding=10)
        device_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def scan_ble_devices():
            self.status_var.set("狀態: 掃描中...")
            self.mainWindow.update()
            threading.Thread(target=lambda: self._run_scan(device_frame), daemon=True).start()

        scan_btn = ttk.Button(btn_frame, text="掃描藍芽設備", command=scan_ble_devices)
        scan_btn.pack(side=tk.LEFT, padx=(0,5))

        clear_btn = ttk.Button(btn_frame, text="清除列表", command=lambda: self.clear_devices(device_frame))
        clear_btn.pack(side=tk.LEFT)

        open_btn = ttk.Button(btn_frame, text="燈光開關", command=lambda: self.open_close_devices(device_frame))
        open_btn.pack(side=tk.LEFT, padx=30)

        self.mainWindow.mainloop()

    def _run_scan(self, device_frame):
        # 後台掃描
        try:
            ble_manager = BleManager()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            devices = loop.run_until_complete(ble_manager.discover_devices())
            self.deviced_light = devices
            loop.close()
            
            self.clear_devices(device_frame)

            if devices:
                for device in devices:
                    device_btn = ttk.Button(
                        device_frame,
                        text=f"「{device.name}」 : {device.address}",
                        padding=5
                    )
                    device_btn.config(command=lambda d=device, btn = device_btn: self._on_device_select(d, btn))
                    device_btn.pack(fill=tk.X, pady=2)
            else:
                self.status_var.set("狀態: 未找到任何設備") 
        except Exception as e:
            self.status_var.set(f"狀態: 掃描失敗 - {str(e)}")
            print("EXCP!! :"+str(e))

    def _on_device_select(self, device, btn):
        # 選取設備
        self.status_var.set(f"狀態: 連線「{device.name}」 - 地址為「{device.address}」")
        threading.Thread(target=lambda: self._connect_device(device, btn), daemon=True).start()

    def _connect_device(self, device, btn):
        #連線該設備
        ble_manager = BleManager()
        loop = asyncio.new_event_loop()           # 建立新的事件迴圈
        asyncio.set_event_loop(loop)              # 設定為目前執行緒的事件迴圈
        result = loop.run_until_complete(ble_manager.connect_device(device.address))    # 用迴圈執行非同步函式，等到完成
        loop.close()                               # 關閉迴圈，釋放資源
        
        btn_style = ttk.Style()
        if result:
            #print("OK")
            btn_style.configure("Success.TButton", background="green")
            btn.config(style="Success.TButton")
            self.status_var.set(f"狀態: 連線「{device.name}」 - 結果為「成功」")
            self.connected_light[device.name] = device.address
        else:
            #print("Fail")
            btn_style.configure("Failed.TButton", background="red")
            btn.config(style="Failed.TButton")
            self.status_var.set(f"狀態: 連線「{device.name}」 - 結果為「失敗」")

    def clear_devices(self, device_frame):
        # 清除設備列表
        for widget in device_frame.winfo_children():
            widget.destroy()

    def open_close_devices(self, device_frame):
        
        return

def create_main_window():
    #建立並運行主視窗
    MainWindow()