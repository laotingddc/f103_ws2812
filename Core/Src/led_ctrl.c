/**
 * @file    led_ctrl.c
 * @brief   LED控制协议模块实现
 */
#include "led_ctrl.h"
#include "ws2812.h"
#include "usart.h"
#include "gpio.h"
#include <string.h>

/* 接收状态机 */
typedef enum {
    RX_WAIT_HEAD,
    RX_WAIT_CMD,
    RX_WAIT_DATA,
} RxState_t;

/* 闪烁控制结构 */
typedef struct {
    uint8_t enabled;
    uint8_t state;      // 0=off, 1=on
    uint8_t r, g, b;
    uint16_t period;    // 闪烁周期(ms)
    uint16_t counter;   // 计数器
} BlinkCtrl_t;

/* 私有变量 */
static UART_HandleTypeDef *led_huart;
static uint8_t rx_byte;
static uint8_t rx_buf[LED_RX_BUF_SIZE];
static uint8_t rx_idx = 0;
static RxState_t rx_state = RX_WAIT_HEAD;
static uint8_t rx_cmd = 0;
static uint8_t rx_len = 0;
static volatile uint8_t frame_ready = 0;

static BlinkCtrl_t blink_ctrl[WS2812_NUM_LEDS];
static uint8_t blink_all_enabled = 0;
static BlinkCtrl_t blink_all_ctrl;

typedef struct {
    GPIO_TypeDef *port;
    uint16_t pin;
} GpioChannelMap_t;

/* GPIO通道映射（高电平有效）
 * CH0~CH15:
 * PA2,PA3,PA4,PA5,PA6,PA7,PA8,PB0,PB1,PB2,PB10,PB11,PB12,PB13,PB14,PB15
 */
static const GpioChannelMap_t gpio_channels[16] = {
    {GPIOA, GPIO_PIN_2},
    {GPIOA, GPIO_PIN_3},
    {GPIOA, GPIO_PIN_4},
    {GPIOA, GPIO_PIN_5},
    {GPIOA, GPIO_PIN_6},
    {GPIOA, GPIO_PIN_7},
    {GPIOA, GPIO_PIN_8},
    {GPIOB, GPIO_PIN_0},
    {GPIOB, GPIO_PIN_1},
    {GPIOB, GPIO_PIN_2},
    {GPIOB, GPIO_PIN_10},
    {GPIOB, GPIO_PIN_11},
    {GPIOB, GPIO_PIN_12},
    {GPIOB, GPIO_PIN_13},
    {GPIOB, GPIO_PIN_14},
    {GPIOB, GPIO_PIN_15}
};

static void gpio_set_channel(uint16_t ch, uint8_t val)
{
    if (ch < 16) {
        HAL_GPIO_WritePin(gpio_channels[ch].port,
                          gpio_channels[ch].pin,
                          val ? GPIO_PIN_SET : GPIO_PIN_RESET);
    }
}

static void gpio_set_mask(uint16_t mask)
{
    for (uint16_t ch = 0; ch < 16; ch++) {
        gpio_set_channel(ch, (mask >> ch) & 0x01);
    }
}

/* 命令长度表 (不含帧头和校验和) */
static uint8_t get_cmd_len(uint8_t cmd)
{
    switch (cmd) {
        case CMD_SET_PIXEL:     return 6;  // cmd + idx(2) + rgb(3)
        case CMD_SET_ALL:       return 4;  // cmd + rgb(3)
        case CMD_OFF_PIXEL:     return 3;  // cmd + idx(2)
        case CMD_OFF_ALL:       return 1;  // cmd
        case CMD_BLINK_PIXEL:   return 8;  // cmd + idx(2) + rgb(3) + period(2)
        case CMD_BLINK_STOP:    return 3;  // cmd + idx(2)
        case CMD_BLINK_ALL:     return 6;  // cmd + rgb(3) + period(2)
        case CMD_BLINK_ALL_STOP:return 1;  // cmd
        case CMD_SET_RANGE:     return 8;  // cmd + start(2) + end(2) + rgb(3)
        case CMD_GPIO_SET:      return 4;  // cmd + ch(2) + val(1)
        case CMD_GPIO_SET_MASK: return 3;  // cmd + mask(2)
        case CMD_GPIO_OFF_ALL:  return 1;  // cmd
        default: return 0;
    }
}

/* 校验和计算 */
static uint8_t calc_checksum(uint8_t *data, uint8_t len)
{
    uint8_t sum = 0;
    for (uint8_t i = 0; i < len; i++) {
        sum += data[i];
    }
    return sum;
}

/* 处理接收到的命令 */
static void process_command(void)
{
    uint8_t cmd = rx_buf[0];
    uint16_t idx, start, end;
    uint8_t r, g, b;
    uint16_t period;
    uint16_t ch, mask;
    uint8_t gpio_val;
    uint8_t need_ws2812_update = 1;
    
    switch (cmd) {
        case CMD_SET_PIXEL:
            idx = rx_buf[1] | (rx_buf[2] << 8);
            r = rx_buf[3]; g = rx_buf[4]; b = rx_buf[5];
            if (idx < WS2812_NUM_LEDS) {
                blink_ctrl[idx].enabled = 0;
                WS2812_SetPixel(idx, r, g, b);
            }
            break;
            
        case CMD_SET_ALL:
            r = rx_buf[1]; g = rx_buf[2]; b = rx_buf[3];
            blink_all_enabled = 0;
            memset(blink_ctrl, 0, sizeof(blink_ctrl));
            WS2812_SetAll(r, g, b);
            break;
            
        case CMD_OFF_PIXEL:
            idx = rx_buf[1] | (rx_buf[2] << 8);
            if (idx < WS2812_NUM_LEDS) {
                blink_ctrl[idx].enabled = 0;
                WS2812_SetPixel(idx, 0, 0, 0);
            }
            break;
            
        case CMD_OFF_ALL:
            blink_all_enabled = 0;
            memset(blink_ctrl, 0, sizeof(blink_ctrl));
            WS2812_Clear();
            break;
            
        case CMD_BLINK_PIXEL:
            idx = rx_buf[1] | (rx_buf[2] << 8);
            r = rx_buf[3]; g = rx_buf[4]; b = rx_buf[5];
            period = rx_buf[6] | (rx_buf[7] << 8);
            if (idx < WS2812_NUM_LEDS && period > 0) {
                blink_ctrl[idx].enabled = 1;
                blink_ctrl[idx].r = r;
                blink_ctrl[idx].g = g;
                blink_ctrl[idx].b = b;
                blink_ctrl[idx].period = period;
                blink_ctrl[idx].counter = 0;
                blink_ctrl[idx].state = 1;
                WS2812_SetPixel(idx, r, g, b);
            }
            break;
            
        case CMD_BLINK_STOP:
            idx = rx_buf[1] | (rx_buf[2] << 8);
            if (idx < WS2812_NUM_LEDS) {
                blink_ctrl[idx].enabled = 0;
            }
            break;
            
        case CMD_BLINK_ALL:
            r = rx_buf[1]; g = rx_buf[2]; b = rx_buf[3];
            period = rx_buf[4] | (rx_buf[5] << 8);
            if (period > 0) {
                memset(blink_ctrl, 0, sizeof(blink_ctrl));
                blink_all_enabled = 1;
                blink_all_ctrl.r = r;
                blink_all_ctrl.g = g;
                blink_all_ctrl.b = b;
                blink_all_ctrl.period = period;
                blink_all_ctrl.counter = 0;
                blink_all_ctrl.state = 1;
                WS2812_SetAll(r, g, b);
            }
            break;
            
        case CMD_BLINK_ALL_STOP:
            blink_all_enabled = 0;
            break;
            
        case CMD_SET_RANGE:
            start = rx_buf[1] | (rx_buf[2] << 8);
            end = rx_buf[3] | (rx_buf[4] << 8);
            r = rx_buf[5]; g = rx_buf[6]; b = rx_buf[7];
            if (start < WS2812_NUM_LEDS && end < WS2812_NUM_LEDS && start <= end) {
                for (uint16_t i = start; i <= end; i++) {
                    blink_ctrl[i].enabled = 0;
                    WS2812_SetPixel(i, r, g, b);
                }
            }
            break;

        case CMD_GPIO_SET:
            ch = rx_buf[1] | (rx_buf[2] << 8);
            gpio_val = rx_buf[3] ? 1 : 0;
            gpio_set_channel(ch, gpio_val);
            need_ws2812_update = 0;
            break;

        case CMD_GPIO_SET_MASK:
            mask = rx_buf[1] | (rx_buf[2] << 8);
            gpio_set_mask(mask);
            need_ws2812_update = 0;
            break;

        case CMD_GPIO_OFF_ALL:
            gpio_set_mask(0x0000);
            need_ws2812_update = 0;
            break;
    }
    
    if (need_ws2812_update) {
        WS2812_Update();
    }
}

/**
 * @brief  初始化LED控制模块
 */
void LED_Ctrl_Init(UART_HandleTypeDef *huart)
{
    led_huart = huart;
    rx_state = RX_WAIT_HEAD;
    rx_idx = 0;
    frame_ready = 0;
    
    memset(blink_ctrl, 0, sizeof(blink_ctrl));
    blink_all_enabled = 0;
    
    // 启动串口接收
    HAL_UART_Receive_IT(led_huart, &rx_byte, 1);
}

/**
 * @brief  串口接收回调 (在HAL_UART_RxCpltCallback中调用)
 */
void LED_Ctrl_RxCallback(void)
{
    switch (rx_state) {
        case RX_WAIT_HEAD:
            if (rx_byte == LED_FRAME_HEAD) {
                rx_state = RX_WAIT_CMD;
                rx_idx = 0;
            }
            break;
            
        case RX_WAIT_CMD:
            rx_cmd = rx_byte;
            rx_len = get_cmd_len(rx_cmd);
            if (rx_len > 0) {
                rx_buf[rx_idx++] = rx_byte;
                rx_state = RX_WAIT_DATA;
            } else {
                rx_state = RX_WAIT_HEAD;
            }
            break;
            
        case RX_WAIT_DATA:
            rx_buf[rx_idx++] = rx_byte;
            // 检查是否接收完成 (数据 + 校验和)
            if (rx_idx >= rx_len + 1) {
                // 验证校验和
                uint8_t checksum = calc_checksum(rx_buf, rx_len);
                if (checksum == rx_buf[rx_len]) {
                    frame_ready = 1;
                }
                rx_state = RX_WAIT_HEAD;
                rx_idx = 0;
            }
            break;
    }
    
    // 继续接收
    HAL_UART_Receive_IT(led_huart, &rx_byte, 1);
}

/**
 * @brief  主循环处理函数
 */
void LED_Ctrl_Process(void)
{
    if (frame_ready) {
        frame_ready = 0;
        process_command();
    }
}

/**
 * @brief  定时器回调 (1ms调用一次，用于闪烁控制)
 */
void LED_Ctrl_TimerCallback(void)
{
    uint8_t need_update = 0;
    
    // 全局闪烁
    if (blink_all_enabled) {
        blink_all_ctrl.counter++;
        if (blink_all_ctrl.counter >= blink_all_ctrl.period / 2) {
            blink_all_ctrl.counter = 0;
            blink_all_ctrl.state = !blink_all_ctrl.state;
            if (blink_all_ctrl.state) {
                WS2812_SetAll(blink_all_ctrl.r, blink_all_ctrl.g, blink_all_ctrl.b);
            } else {
                WS2812_Clear();
            }
            need_update = 1;
        }
    } else {
        // 单独LED闪烁
        for (uint16_t i = 0; i < WS2812_NUM_LEDS; i++) {
            if (blink_ctrl[i].enabled) {
                blink_ctrl[i].counter++;
                if (blink_ctrl[i].counter >= blink_ctrl[i].period / 2) {
                    blink_ctrl[i].counter = 0;
                    blink_ctrl[i].state = !blink_ctrl[i].state;
                    if (blink_ctrl[i].state) {
                        WS2812_SetPixel(i, blink_ctrl[i].r, blink_ctrl[i].g, blink_ctrl[i].b);
                    } else {
                        WS2812_SetPixel(i, 0, 0, 0);
                    }
                    need_update = 1;
                }
            }
        }
    }
    
    if (need_update && !WS2812_IsBusy()) {
        WS2812_Update();
    }
}
