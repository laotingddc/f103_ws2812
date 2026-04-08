/**
 * @file    led_ctrl.h
 * @brief   LED控制协议模块
 * 
 * 通信协议格式 (二进制):
 * | 帧头 | 命令 | LED索引(2B) | 参数... | 校验和 |
 * | 0xAA | CMD  | IDX_L IDX_H | ...     | SUM    |
 * 
 * 命令列表:
 * 0x01 - 设置单个LED颜色:  AA 01 IDX_L IDX_H R G B SUM
 * 0x02 - 设置所有LED颜色:  AA 02 R G B SUM
 * 0x03 - 关闭单个LED:      AA 03 IDX_L IDX_H SUM
 * 0x04 - 关闭所有LED:      AA 04 SUM
 * 0x05 - 设置LED闪烁:      AA 05 IDX_L IDX_H R G B PERIOD_MS(2B) SUM
 * 0x06 - 停止LED闪烁:      AA 06 IDX_L IDX_H SUM
 * 0x07 - 设置所有LED闪烁:  AA 07 R G B PERIOD_MS(2B) SUM
 * 0x08 - 停止所有LED闪烁:  AA 08 SUM
 * 0x09 - 设置范围LED颜色:  AA 09 START_L START_H END_L END_H R G B SUM
 * 0x0A - 设置单路GPIO:     AA 0A CH_L CH_H VAL SUM
 *                            CH: 0~15, VAL: 0=低电平(关), 1=高电平(开)
 * 0x0B - 设置16路GPIO位图:  AA 0B MASK_L MASK_H SUM
 *                            bit0->CH0 ... bit15->CH15, 1=开, 0=关
 * 0x0C - 关闭所有GPIO:      AA 0C SUM
 * 
 * 校验和: 从命令字节开始到校验和前一字节的累加和(低8位)
 */
#ifndef __LED_CTRL_H__
#define __LED_CTRL_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"

/* 协议定义 */
#define LED_FRAME_HEAD      0xAA
#define LED_RX_BUF_SIZE     32

/* 命令定义 */
#define CMD_SET_PIXEL       0x01
#define CMD_SET_ALL         0x02
#define CMD_OFF_PIXEL       0x03
#define CMD_OFF_ALL         0x04
#define CMD_BLINK_PIXEL     0x05
#define CMD_BLINK_STOP      0x06
#define CMD_BLINK_ALL       0x07
#define CMD_BLINK_ALL_STOP  0x08
#define CMD_SET_RANGE       0x09
#define CMD_GPIO_SET        0x0A
#define CMD_GPIO_SET_MASK   0x0B
#define CMD_GPIO_OFF_ALL    0x0C

/* 函数声明 */
void LED_Ctrl_Init(UART_HandleTypeDef *huart);
void LED_Ctrl_Process(void);      // 在主循环中调用
void LED_Ctrl_RxCallback(void);   // 在串口接收中断中调用
void LED_Ctrl_TimerCallback(void); // 在1ms定时器中断中调用(用于闪烁)

#ifdef __cplusplus
}
#endif

#endif /* __LED_CTRL_H__ */
