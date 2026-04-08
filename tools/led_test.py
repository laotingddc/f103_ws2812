#!/usr/bin/env python3
"""
WS2812 LED串口控制上位机测试程序
使用方法: python led_test.py [COM端口]
"""

import serial
import time
import sys
import threading

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


class LEDController:
    def __init__(self, port, baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        self.running = True
        time.sleep(0.1)
        print(f"已连接到 {port}")
        
        # 启动接收线程
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()

    def _rx_loop(self):
        """接收线程"""
        while self.running:
            try:
                data = self.ser.read(100)
                if data:
                    print(f"\n[接收] {data.hex(' ').upper()}")
                    # 尝试解析为ASCII
                    try:
                        text = data.decode('utf-8', errors='ignore')
                        if text.isprintable():
                            print(f"[ASCII] {text}")
                    except:
                        pass
                    print("> ", end="", flush=True)
            except:
                pass

    def close(self):
        self.running = False
        time.sleep(0.2)
        self.ser.close()

    def _calc_checksum(self, data):
        """计算校验和"""
        return sum(data) & 0xFF

    def _send_frame(self, data):
        """发送数据帧"""
        checksum = self._calc_checksum(data)
        frame = bytes([FRAME_HEAD] + data + [checksum])
        self.ser.write(frame)
        print(f"[发送] {frame.hex(' ').upper()}")

    def send_raw(self, hex_str):
        """发送原始十六进制数据"""
        try:
            # 移除空格和常见分隔符
            hex_str = hex_str.replace(" ", "").replace(",", "").replace("0x", "").replace("0X", "")
            data = bytes.fromhex(hex_str)
            self.ser.write(data)
            print(f"[发送] {data.hex(' ').upper()}")
        except ValueError as e:
            print(f"十六进制格式错误: {e}")

    def set_pixel(self, index, r, g, b):
        """设置单个LED颜色"""
        data = [CMD_SET_PIXEL, index & 0xFF, (index >> 8) & 0xFF, r, g, b]
        self._send_frame(data)

    def set_all(self, r, g, b):
        """设置所有LED颜色"""
        data = [CMD_SET_ALL, r, g, b]
        self._send_frame(data)

    def off_pixel(self, index):
        """关闭单个LED"""
        data = [CMD_OFF_PIXEL, index & 0xFF, (index >> 8) & 0xFF]
        self._send_frame(data)

    def off_all(self):
        """关闭所有LED"""
        data = [CMD_OFF_ALL]
        self._send_frame(data)

    def blink_pixel(self, index, r, g, b, period_ms):
        """设置单个LED闪烁"""
        data = [CMD_BLINK_PIXEL, index & 0xFF, (index >> 8) & 0xFF,
                r, g, b, period_ms & 0xFF, (period_ms >> 8) & 0xFF]
        self._send_frame(data)

    def blink_stop(self, index):
        """停止单个LED闪烁"""
        data = [CMD_BLINK_STOP, index & 0xFF, (index >> 8) & 0xFF]
        self._send_frame(data)

    def blink_all(self, r, g, b, period_ms):
        """设置所有LED闪烁"""
        data = [CMD_BLINK_ALL, r, g, b, period_ms & 0xFF, (period_ms >> 8) & 0xFF]
        self._send_frame(data)

    def blink_all_stop(self):
        """停止所有LED闪烁"""
        data = [CMD_BLINK_ALL_STOP]
        self._send_frame(data)

    def set_range(self, start, end, r, g, b):
        """设置范围LED颜色"""
        data = [CMD_SET_RANGE,
                start & 0xFF, (start >> 8) & 0xFF,
                end & 0xFF, (end >> 8) & 0xFF,
                r, g, b]
        self._send_frame(data)

    def gpio_set(self, ch, value):
        """设置单路GPIO: ch=0~15, value=0/1"""
        data = [CMD_GPIO_SET, ch & 0xFF, (ch >> 8) & 0xFF, 1 if value else 0]
        self._send_frame(data)

    def gpio_set_mask(self, mask):
        """设置16路GPIO位图"""
        data = [CMD_GPIO_SET_MASK, mask & 0xFF, (mask >> 8) & 0xFF]
        self._send_frame(data)

    def gpio_off_all(self):
        """关闭所有GPIO"""
        data = [CMD_GPIO_OFF_ALL]
        self._send_frame(data)


def demo_test(led):
    """演示测试"""
    print("\n=== LED控制演示测试 ===\n")

    print("1. 关闭所有LED")
    led.off_all()
    time.sleep(0.5)

    print("2. 所有LED红色")
    led.set_all(255, 0, 0)
    time.sleep(1)

    print("3. 所有LED绿色")
    led.set_all(0, 255, 0)
    time.sleep(1)

    print("4. 所有LED蓝色")
    led.set_all(0, 0, 255)
    time.sleep(1)

    print("5. 关闭所有LED")
    led.off_all()
    time.sleep(0.5)

    print("6. 逐个点亮前10个LED (彩虹色)")
    colors = [
        (255, 0, 0), (255, 127, 0), (255, 255, 0), (127, 255, 0), (0, 255, 0),
        (0, 255, 127), (0, 255, 255), (0, 127, 255), (0, 0, 255), (127, 0, 255)
    ]
    for i, (r, g, b) in enumerate(colors):
        led.set_pixel(i, r, g, b)
        time.sleep(0.1)
    time.sleep(1)

    print("7. 设置第10-20个LED为白色")
    led.set_range(10, 20, 255, 255, 255)
    time.sleep(1)

    print("8. 第0个LED红色闪烁 (500ms周期)")
    led.off_all()
    time.sleep(0.2)
    led.blink_pixel(0, 255, 0, 0, 500)
    time.sleep(3)

    print("9. 停止闪烁")
    led.blink_stop(0)
    time.sleep(0.5)

    print("10. 所有LED蓝色闪烁 (1000ms周期)")
    led.blink_all(0, 0, 255, 1000)
    time.sleep(4)

    print("11. 停止所有闪烁")
    led.blink_all_stop()
    time.sleep(0.5)

    print("12. 关闭所有LED")
    led.off_all()

    print("\n=== 测试完成 ===\n")


def print_help():
    """打印帮助信息"""
    print("""
=== 命令帮助 ===
快捷命令:
  all r g b        - 设置所有LED颜色 (例: all 255 0 0)
  pixel i r g b    - 设置单个LED颜色 (例: pixel 0 255 0 0)
  range s e r g b  - 设置范围LED颜色 (例: range 0 10 0 255 0)
  off              - 关闭所有LED
  off i            - 关闭单个LED (例: off 5)
  blink i r g b p  - LED闪烁 (例: blink 0 255 0 0 500)
  blinkall r g b p - 所有LED闪烁 (例: blinkall 0 0 255 1000)
  stop             - 停止所有闪烁
  stop i           - 停止单个LED闪烁
  gpio i on/off    - 设置单路GPIO (例: gpio 0 on)
  gpiomask mask    - 按位图设置16路GPIO (例: gpiomask 0x00FF)
  gpiooff          - 关闭所有GPIO
  demo             - 运行演示

原始数据发送:
  hex AA01000000FF000000  - 发送十六进制数据
  hex AA 01 00 00 FF 00 00 00  - 支持空格分隔

其他:
  help             - 显示帮助
  quit/q           - 退出
""")


def interactive_mode(led):
    """交互模式"""
    print("\n=== 交互模式 (输入 help 查看帮助) ===\n")

    while True:
        try:
            cmd = input("> ").strip().split()
            if not cmd:
                continue

            cmd_lower = cmd[0].lower()

            if cmd_lower == "quit" or cmd_lower == "q":
                break
            elif cmd_lower == "help" or cmd_lower == "h":
                print_help()
            elif cmd_lower == "demo":
                demo_test(led)
            elif cmd_lower == "hex" and len(cmd) >= 2:
                # 发送原始十六进制数据
                hex_data = "".join(cmd[1:])
                led.send_raw(hex_data)
            elif cmd_lower == "all" and len(cmd) == 4:
                led.set_all(int(cmd[1]), int(cmd[2]), int(cmd[3]))
            elif cmd_lower == "pixel" and len(cmd) == 5:
                led.set_pixel(int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4]))
            elif cmd_lower == "range" and len(cmd) == 6:
                led.set_range(int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4]), int(cmd[5]))
            elif cmd_lower == "off":
                if len(cmd) == 1:
                    led.off_all()
                else:
                    led.off_pixel(int(cmd[1]))
            elif cmd_lower == "blink" and len(cmd) == 6:
                led.blink_pixel(int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4]), int(cmd[5]))
            elif cmd_lower == "blinkall" and len(cmd) == 5:
                led.blink_all(int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4]))
            elif cmd_lower == "stop":
                if len(cmd) == 1:
                    led.blink_all_stop()
                else:
                    led.blink_stop(int(cmd[1]))
            elif cmd_lower == "gpio" and len(cmd) == 3:
                ch = int(cmd[1], 0)
                state = cmd[2].lower()
                if state in ("on", "1", "high"):
                    led.gpio_set(ch, 1)
                elif state in ("off", "0", "low"):
                    led.gpio_set(ch, 0)
                else:
                    print("gpio命令格式: gpio <ch> on/off")
            elif cmd_lower == "gpiomask" and len(cmd) == 2:
                mask = int(cmd[1], 0)
                led.gpio_set_mask(mask)
            elif cmd_lower == "gpiooff":
                led.gpio_off_all()
            else:
                # 尝试作为十六进制数据发送
                try:
                    hex_data = "".join(cmd)
                    if all(c in '0123456789abcdefABCDEF' for c in hex_data.replace(" ", "")):
                        led.send_raw(hex_data)
                    else:
                        print("未知命令，输入 help 查看帮助")
                except:
                    print("未知命令，输入 help 查看帮助")
        except ValueError:
            print("参数格式错误")
        except KeyboardInterrupt:
            print()
            break


def main():
    if len(sys.argv) < 2:
        print("WS2812 LED串口控制工具")
        print("用法: python led_test.py <COM端口> [demo]")
        print("示例: python led_test.py COM3")
        print("      python led_test.py COM3 demo")
        sys.exit(1)

    port = sys.argv[1]
    
    try:
        led = LEDController(port)
    except serial.SerialException as e:
        print(f"无法打开串口: {e}")
        sys.exit(1)

    try:
        if len(sys.argv) > 2 and sys.argv[2] == "demo":
            demo_test(led)
        else:
            interactive_mode(led)
    finally:
        led.close()
        print("已断开连接")


if __name__ == "__main__":
    main()
