# STM32F103 WS2812 LED控制器

基于STM32F103单片机的WS2812 LED灯带控制器，支持96个LED，通过串口接收命令控制LED的颜色、亮灭和闪烁。

## 功能特性

- 支持96个WS2812 LED
- PWM+DMA驱动，CPU占用低
- 串口命令控制 (115200波特率)
- 支持单个LED、范围LED、全部LED控制
- 支持LED闪烁效果
- 支持16路GPIO输出控制（高电平有效）
- 包含GUI上位机软件

## 硬件连接

| 功能 | 引脚 |
|------|------|
| LED数据线 | PB6 (TIM4_CH1) |
| 串口TX | PA9 |
| 串口RX | PA10 |

### 16路GPIO通道映射（CH0~CH15）

| 通道 | 引脚 |
|------|------|
| CH0  | PA2  |
| CH1  | PA3  |
| CH2  | PA4  |
| CH3  | PA5  |
| CH4  | PA6  |
| CH5  | PA7  |
| CH6  | PA8  |
| CH7  | PB0  |
| CH8  | PB1  |
| CH9  | PB2  |
| CH10 | PB10 |
| CH11 | PB11 |
| CH12 | PB12 |
| CH13 | PB13 |
| CH14 | PB14 |
| CH15 | PB15 |

GPIO控制逻辑：高电平有效（`1=开`，`0=关`）。

## 编译

```bash
cmake --preset Debug
cmake --build build/Debug
```

## 串口协议

详细协议说明见 [docs/protocol.md](docs/protocol.md)

### 快速参考

| 命令 | 功能 | 格式 |
|------|------|------|
| 0x01 | 设置单个LED | `AA 01 IDX_L IDX_H R G B SUM` |
| 0x02 | 设置所有LED | `AA 02 R G B SUM` |
| 0x03 | 关闭单个LED | `AA 03 IDX_L IDX_H SUM` |
| 0x04 | 关闭所有LED | `AA 04 SUM` |
| 0x05 | LED闪烁 | `AA 05 IDX_L IDX_H R G B PERIOD_L PERIOD_H SUM` |
| 0x06 | 停止闪烁 | `AA 06 IDX_L IDX_H SUM` |
| 0x07 | 所有LED闪烁 | `AA 07 R G B PERIOD_L PERIOD_H SUM` |
| 0x08 | 停止所有闪烁 | `AA 08 SUM` |
| 0x09 | 设置范围LED | `AA 09 START_L START_H END_L END_H R G B SUM` |
| 0x0A | 设置单路GPIO | `AA 0A CH_L CH_H VAL SUM` |
| 0x0B | 设置16路GPIO位图 | `AA 0B MASK_L MASK_H SUM` |
| 0x0C | 关闭所有GPIO | `AA 0C SUM` |

校验和 = 从命令字节到校验和前一字节的累加和(低8位)

### 示例

设置所有LED为红色:
```
AA 02 FF 00 00 01
```

设置GPIO通道0为高电平:
```
AA 0A 00 00 01 0B
```

## 上位机软件

### GUI版本

直接运行 `tools/dist/LED控制器.exe`

或从源码运行:
```bash
pip install pyserial
python tools/led_gui.py
```

功能:
- 串口自动检测
- 颜色选择器
- LED控制按钮
- 16路GPIO控制（单路/全开/全关/位图下发）
- 原始数据发送
- 通信日志

### 命令行版本

```bash
python tools/led_test.py COM3
```

## 项目结构

```
├── Core/
│   ├── Inc/
│   │   ├── ws2812.h      # WS2812驱动头文件
│   │   └── led_ctrl.h    # LED控制协议头文件
│   └── Src/
│       ├── ws2812.c      # WS2812驱动实现
│       ├── led_ctrl.c    # LED控制协议实现
│       └── main.c        # 主程序
├── docs/
│   └── protocol.md       # 通信协议文档
├── tools/
│   ├── led_gui.py        # GUI上位机源码
│   ├── led_test.py       # 命令行上位机
│   └── dist/
│       └── LED控制器.exe  # 打包好的上位机
└── README.md
```

## API说明

```c
// 初始化
WS2812_Init(&htim4, TIM_CHANNEL_1);
LED_Ctrl_Init(&huart1);

// 设置单个LED颜色
WS2812_SetPixel(index, r, g, b);

// 设置所有LED颜色
WS2812_SetAll(r, g, b);

// 关闭所有LED
WS2812_Clear();

// 更新显示
WS2812_Update();
```

## License

MIT
