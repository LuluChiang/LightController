import tkinter as tk
from tkinter import ttk
import threading
import asyncio
from ble_func import discover_devices

# CONFIG
FONT_CH = "微軟正黑體"
FONT_EN = "Calibri"
FONT_SIZE = 14

def create_main_window():
    # 建立主視窗
    mainWindow = tk.Tk()
    mainWindow.title("Light Controller")
    mainWindow.geometry("640x640+500+200")    
    mainWindow.resizable(False, False)

    status_var = tk.StringVar(value="狀態: 未掃描")
    status_label = ttk.Label(mainWindow, textvariable=status_var, font=(FONT_CH, FONT_SIZE))
    status_label.pack(anchor="w", padx=10, pady=5)

    btn_frame = ttk.Frame(mainWindow, padding=10)
    btn_frame.pack(fill=tk.X)

    device_frame = ttk.LabelFrame(mainWindow, text="設備列表(點擊連線)", padding=10, font=(FONT_CH, FONT_SIZE))
    device_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def scan_ble_devices():
        status_var.set("狀態: 掃描中...")
        mainWindow.update()
        threading.Thread(target=lambda: _run_scan(status_var, device_frame), daemon=True).start()

    scan_btn = ttk.Button(btn_frame, text="掃描藍芽設備", command=scan_ble_devices)
    scan_btn.pack(side=tk.LEFT, padx=(0,5))

    clear_btn = ttk.Button(btn_frame, text="清除列表", command=lambda: clear_devices(device_frame))
    clear_btn.pack(side=tk.LEFT)

    mainWindow.mainloop()

def _run_scan(status_var, device_frame):
    # 後台掃描
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        devices = loop.run_until_complete(discover_devices())
        loop.close()
        
        clear_devices(device_frame)

        if devices:
            for device in devices:
                device_btn = ttk.Button(
                    device_frame,
                    text=f"「{device.name}」 : {device.address}",
                    command=lambda d=device: _on_device_select(d, status_var),
                    padding=5
                )
                device_btn.pack(fill=tk.X, pady=2)
        else:
            status_var.set("狀態: 未找到任何設備")
    
    except Exception as e:
        status_var.set(f"狀態: 掃描失敗 - {str(e)}")

def _on_device_select(device, status_var):
    # 選取設備
    status_var.set(f"狀態: 選取 {device.name} - {device.address}")

def clear_devices(device_frame):
    # 清除設備列表
    for widget in device_frame.winfo_children():
        widget.destroy()