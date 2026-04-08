#!/usr/bin/env python3
"""
WS2812 LED串口控制上位机 - GUI版本
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, colorchooser
import serial
import serial.tools.list_ports
import threading
import time

# 命令定义
CMD_SET_PIXEL = 0x01
CMD_SET_ALL = 0x02
CMD_OFF_PIXEL = 0x03
CMD_OFF_ALL = 0x04
CMD_BLINK_PIXEL = 0x05
CMD_BLINK_STOP = 0x06
CMD_BLINK_ALL = 0x07
CMD_BLINK_ALL_STOP = 0x08
CMD_SET_RANGE = 0x09
CMD_GPIO_SET = 0x0A
CMD_GPIO_SET_MASK = 0x0B
CMD_GPIO_OFF_ALL = 0x0C
FRAME_HEAD = 0xAA

NUM_LEDS = 96
NUM_GPIOS = 16


class LEDControllerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WS2812 LED控制器")
        self.root.geometry("800x600")
        
        self.ser = None
        self.running = False
        self.current_color = (255, 0, 0)
        self.gpio_vars = [tk.IntVar(value=0) for _ in range(NUM_GPIOS)]
        
        self.create_widgets()
        self.refresh_ports()

    def create_widgets(self):
        # 串口连接区域
        conn_frame = ttk.LabelFrame(self.root, text="串口连接", padding=10)
        conn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(conn_frame, text="端口:").pack(side=tk.LEFT)
        self.port_combo = ttk.Combobox(conn_frame, width=15)
        self.port_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(conn_frame, text="刷新", command=self.refresh_ports).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(conn_frame, text="波特率:").pack(side=tk.LEFT, padx=(10, 0))
        self.baud_combo = ttk.Combobox(conn_frame, width=10, values=["9600", "115200", "256000"])
        self.baud_combo.set("115200")
        self.baud_combo.pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="连接", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=10)
        
        self.status_label = ttk.Label(conn_frame, text="未连接", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # 颜色选择区域
        color_frame = ttk.LabelFrame(self.root, text="颜色选择", padding=10)
        color_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.color_btn = tk.Button(color_frame, text="选择颜色", width=10, bg="#FF0000", 
                                   command=self.choose_color)
        self.color_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(color_frame, text="R:").pack(side=tk.LEFT)
        self.r_var = tk.StringVar(value="255")
        self.r_entry = ttk.Entry(color_frame, width=5, textvariable=self.r_var)
        self.r_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(color_frame, text="G:").pack(side=tk.LEFT)
        self.g_var = tk.StringVar(value="0")
        self.g_entry = ttk.Entry(color_frame, width=5, textvariable=self.g_var)
        self.g_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(color_frame, text="B:").pack(side=tk.LEFT)
        self.b_var = tk.StringVar(value="0")
        self.b_entry = ttk.Entry(color_frame, width=5, textvariable=self.b_var)
        self.b_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(color_frame, text="应用RGB", command=self.apply_rgb).pack(side=tk.LEFT, padx=10)

        # LED控制区域
        ctrl_frame = ttk.LabelFrame(self.root, text="LED控制", padding=10)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 第一行
        row1 = ttk.Frame(ctrl_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="LED索引:").pack(side=tk.LEFT)
        self.led_index = ttk.Spinbox(row1, from_=0, to=NUM_LEDS-1, width=8)
        self.led_index.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(row1, text="设置单个LED", command=self.set_pixel).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="关闭单个LED", command=self.off_pixel).pack(side=tk.LEFT, padx=5)
        
        # 第二行
        row2 = ttk.Frame(ctrl_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Button(row2, text="设置所有LED", command=self.set_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="关闭所有LED", command=self.off_all).pack(side=tk.LEFT, padx=5)
        
        # 第三行 - 范围设置
        row3 = ttk.Frame(ctrl_frame)
        row3.pack(fill=tk.X, pady=2)
        
        ttk.Label(row3, text="范围:").pack(side=tk.LEFT)
        self.range_start = ttk.Spinbox(row3, from_=0, to=NUM_LEDS-1, width=6)
        self.range_start.pack(side=tk.LEFT, padx=2)
        ttk.Label(row3, text="到").pack(side=tk.LEFT)
        self.range_end = ttk.Spinbox(row3, from_=0, to=NUM_LEDS-1, width=6)
        self.range_end.set(str(NUM_LEDS-1))
        self.range_end.pack(side=tk.LEFT, padx=2)
        ttk.Button(row3, text="设置范围", command=self.set_range).pack(side=tk.LEFT, padx=10)

        # 闪烁控制区域
        blink_frame = ttk.LabelFrame(self.root, text="闪烁控制", padding=10)
        blink_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(blink_frame, text="闪烁周期(ms):").pack(side=tk.LEFT)
        self.blink_period = ttk.Spinbox(blink_frame, from_=100, to=5000, width=8, increment=100)
        self.blink_period.set("500")
        self.blink_period.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(blink_frame, text="单个LED闪烁", command=self.blink_pixel).pack(side=tk.LEFT, padx=5)
        ttk.Button(blink_frame, text="停止单个闪烁", command=self.blink_stop).pack(side=tk.LEFT, padx=5)
        ttk.Button(blink_frame, text="所有LED闪烁", command=self.blink_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(blink_frame, text="停止所有闪烁", command=self.blink_all_stop).pack(side=tk.LEFT, padx=5)

        # GPIO控制区域
        gpio_frame = ttk.LabelFrame(self.root, text="16路GPIO控制", padding=10)
        gpio_frame.pack(fill=tk.X, padx=10, pady=5)

        gpio_row1 = ttk.Frame(gpio_frame)
        gpio_row1.pack(fill=tk.X, pady=2)
        ttk.Label(gpio_row1, text="通道:").pack(side=tk.LEFT)
        self.gpio_channel = ttk.Spinbox(gpio_row1, from_=0, to=NUM_GPIOS-1, width=6)
        self.gpio_channel.pack(side=tk.LEFT, padx=5)
        ttk.Button(gpio_row1, text="单路打开", command=self.gpio_single_on).pack(side=tk.LEFT, padx=5)
        ttk.Button(gpio_row1, text="单路关闭", command=self.gpio_single_off).pack(side=tk.LEFT, padx=5)

        gpio_row2 = ttk.Frame(gpio_frame)
        gpio_row2.pack(fill=tk.X, pady=2)
        for i in range(NUM_GPIOS):
            chk = ttk.Checkbutton(gpio_row2, text=f"CH{i}", variable=self.gpio_vars[i])
            chk.grid(row=i // 8, column=i % 8, sticky="w", padx=4, pady=1)

        gpio_row3 = ttk.Frame(gpio_frame)
        gpio_row3.pack(fill=tk.X, pady=2)
        ttk.Button(gpio_row3, text="按勾选发送", command=self.gpio_apply_mask).pack(side=tk.LEFT, padx=5)
        ttk.Button(gpio_row3, text="GPIO全开", command=self.gpio_all_on).pack(side=tk.LEFT, padx=5)
        ttk.Button(gpio_row3, text="GPIO全关", command=self.gpio_all_off).pack(side=tk.LEFT, padx=5)

        # 原始数据发送区域
        raw_frame = ttk.LabelFrame(self.root, text="原始数据发送", padding=10)
        raw_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.raw_entry = ttk.Entry(raw_frame, width=50)
        self.raw_entry.pack(side=tk.LEFT, padx=5)
        self.raw_entry.insert(0, "AA 02 FF 00 00 01")
        ttk.Button(raw_frame, text="发送HEX", command=self.send_raw).pack(side=tk.LEFT, padx=5)

        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="通信日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(log_frame, text="清空日志", command=self.clear_log).pack(pady=5)

    def refresh_ports(self):
        """刷新串口列表"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])

    def toggle_connection(self):
        """切换连接状态"""
        if self.ser and self.ser.is_open:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        """连接串口"""
        port = self.port_combo.get()
        baud = int(self.baud_combo.get())
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            self.running = True
            self.rx_thread = threading.Thread(target=self.rx_loop, daemon=True)
            self.rx_thread.start()
            
            self.connect_btn.config(text="断开")
            self.status_label.config(text=f"已连接 {port}", foreground="green")
            self.log(f"已连接到 {port} @ {baud}")
        except Exception as e:
            messagebox.showerror("错误", f"无法连接: {e}")

    def disconnect(self):
        """断开连接"""
        self.running = False
        time.sleep(0.2)
        if self.ser:
            self.ser.close()
        self.connect_btn.config(text="连接")
        self.status_label.config(text="未连接", foreground="red")
        self.log("已断开连接")

    def rx_loop(self):
        """接收线程"""
        while self.running:
            try:
                if self.ser and self.ser.is_open:
                    data = self.ser.read(100)
                    if data:
                        self.log(f"[接收] {data.hex(' ').upper()}")
            except:
                pass

    def log(self, msg):
        """添加日志"""
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)

    def choose_color(self):
        """选择颜色"""
        color = colorchooser.askcolor(title="选择颜色")
        if color[0]:
            r, g, b = [int(c) for c in color[0]]
            self.current_color = (r, g, b)
            self.r_var.set(str(r))
            self.g_var.set(str(g))
            self.b_var.set(str(b))
            self.color_btn.config(bg=color[1])

    def apply_rgb(self):
        """应用RGB值"""
        try:
            r = int(self.r_var.get())
            g = int(self.g_var.get())
            b = int(self.b_var.get())
            self.current_color = (r, g, b)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            self.color_btn.config(bg=hex_color)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的RGB值(0-255)")

    def get_color(self):
        """获取当前颜色"""
        try:
            return (int(self.r_var.get()), int(self.g_var.get()), int(self.b_var.get()))
        except:
            return self.current_color

    def calc_checksum(self, data):
        """计算校验和"""
        return sum(data) & 0xFF

    def send_frame(self, data):
        """发送数据帧"""
        if not self.ser or not self.ser.is_open:
            messagebox.showwarning("警告", "请先连接串口")
            return
        checksum = self.calc_checksum(data)
        frame = bytes([FRAME_HEAD] + data + [checksum])
        self.ser.write(frame)
        self.log(f"[发送] {frame.hex(' ').upper()}")

    def set_pixel(self):
        """设置单个LED"""
        idx = int(self.led_index.get())
        r, g, b = self.get_color()
        data = [CMD_SET_PIXEL, idx & 0xFF, (idx >> 8) & 0xFF, r, g, b]
        self.send_frame(data)

    def off_pixel(self):
        """关闭单个LED"""
        idx = int(self.led_index.get())
        data = [CMD_OFF_PIXEL, idx & 0xFF, (idx >> 8) & 0xFF]
        self.send_frame(data)

    def set_all(self):
        """设置所有LED"""
        r, g, b = self.get_color()
        data = [CMD_SET_ALL, r, g, b]
        self.send_frame(data)

    def off_all(self):
        """关闭所有LED"""
        data = [CMD_OFF_ALL]
        self.send_frame(data)

    def set_range(self):
        """设置范围LED"""
        start = int(self.range_start.get())
        end = int(self.range_end.get())
        r, g, b = self.get_color()
        data = [CMD_SET_RANGE, start & 0xFF, (start >> 8) & 0xFF,
                end & 0xFF, (end >> 8) & 0xFF, r, g, b]
        self.send_frame(data)

    def blink_pixel(self):
        """单个LED闪烁"""
        idx = int(self.led_index.get())
        r, g, b = self.get_color()
        period = int(self.blink_period.get())
        data = [CMD_BLINK_PIXEL, idx & 0xFF, (idx >> 8) & 0xFF,
                r, g, b, period & 0xFF, (period >> 8) & 0xFF]
        self.send_frame(data)

    def blink_stop(self):
        """停止单个LED闪烁"""
        idx = int(self.led_index.get())
        data = [CMD_BLINK_STOP, idx & 0xFF, (idx >> 8) & 0xFF]
        self.send_frame(data)

    def blink_all(self):
        """所有LED闪烁"""
        r, g, b = self.get_color()
        period = int(self.blink_period.get())
        data = [CMD_BLINK_ALL, r, g, b, period & 0xFF, (period >> 8) & 0xFF]
        self.send_frame(data)

    def blink_all_stop(self):
        """停止所有LED闪烁"""
        data = [CMD_BLINK_ALL_STOP]
        self.send_frame(data)

    def _set_gpio_checks_from_mask(self, mask):
        """根据位图更新GUI勾选状态"""
        for i in range(NUM_GPIOS):
            self.gpio_vars[i].set((mask >> i) & 0x01)

    def _get_gpio_mask_from_checks(self):
        """从GUI勾选状态计算位图"""
        mask = 0
        for i in range(NUM_GPIOS):
            if self.gpio_vars[i].get():
                mask |= (1 << i)
        return mask

    def gpio_single_on(self):
        """单路GPIO打开"""
        self.gpio_set_single(1)

    def gpio_single_off(self):
        """单路GPIO关闭"""
        self.gpio_set_single(0)

    def gpio_set_single(self, value):
        """设置单路GPIO，value: 0/1"""
        ch = int(self.gpio_channel.get())
        if ch < 0 or ch >= NUM_GPIOS:
            messagebox.showerror("错误", f"GPIO通道需在0~{NUM_GPIOS-1}")
            return
        data = [CMD_GPIO_SET, ch & 0xFF, (ch >> 8) & 0xFF, 1 if value else 0]
        self.send_frame(data)
        self.gpio_vars[ch].set(1 if value else 0)

    def gpio_apply_mask(self):
        """按勾选状态批量设置GPIO"""
        mask = self._get_gpio_mask_from_checks()
        data = [CMD_GPIO_SET_MASK, mask & 0xFF, (mask >> 8) & 0xFF]
        self.send_frame(data)

    def gpio_all_on(self):
        """打开所有GPIO"""
        mask = (1 << NUM_GPIOS) - 1
        data = [CMD_GPIO_SET_MASK, mask & 0xFF, (mask >> 8) & 0xFF]
        self.send_frame(data)
        self._set_gpio_checks_from_mask(mask)

    def gpio_all_off(self):
        """关闭所有GPIO"""
        data = [CMD_GPIO_OFF_ALL]
        self.send_frame(data)
        self._set_gpio_checks_from_mask(0)

    def send_raw(self):
        """发送原始十六进制数据"""
        if not self.ser or not self.ser.is_open:
            messagebox.showwarning("警告", "请先连接串口")
            return
        try:
            hex_str = self.raw_entry.get().replace(" ", "").replace(",", "")
            data = bytes.fromhex(hex_str)
            self.ser.write(data)
            self.log(f"[发送] {data.hex(' ').upper()}")
        except ValueError as e:
            messagebox.showerror("错误", f"十六进制格式错误: {e}")


def main():
    root = tk.Tk()
    app = LEDControllerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
