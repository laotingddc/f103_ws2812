/**
 * @file    ws2812.c
 * @brief   WS2812 LED驱动 (HAL库版本)
 */
#include "ws2812.h"
#include <string.h>

/* 每个LED 24bit (GRB), 加上复位时间 */
#define RESET_SLOTS     50
#define LED_DATA_SIZE   (WS2812_NUM_LEDS * 24)
#define DMA_BUF_SIZE    (LED_DATA_SIZE + RESET_SLOTS)

/* 私有变量 */
static TIM_HandleTypeDef *ws2812_htim;
static uint32_t ws2812_channel;
static uint16_t dma_buffer[DMA_BUF_SIZE];
static uint8_t led_data[WS2812_NUM_LEDS * 3];  // RGB数据
static volatile uint8_t dma_busy = 0;

#if WS2812_USE_GAMMA
/* Gamma校正表 (gamma=2.2) */
static const uint8_t gamma_table[256] = {
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   1,   1,   1,   1,   1,   1,   1,   1,
    1,   1,   1,   1,   2,   2,   2,   2,   2,   2,   2,   2,   3,   3,   3,   3,
    3,   3,   4,   4,   4,   4,   5,   5,   5,   5,   5,   6,   6,   6,   6,   7,
    7,   7,   8,   8,   8,   9,   9,   9,  10,  10,  10,  11,  11,  11,  12,  12,
   13,  13,  13,  14,  14,  15,  15,  16,  16,  17,  17,  18,  18,  19,  19,  20,
   20,  21,  21,  22,  22,  23,  24,  24,  25,  25,  26,  27,  27,  28,  29,  29,
   30,  31,  31,  32,  33,  33,  34,  35,  36,  36,  37,  38,  39,  39,  40,  41,
   42,  43,  43,  44,  45,  46,  47,  48,  49,  49,  50,  51,  52,  53,  54,  55,
   56,  57,  58,  59,  60,  61,  62,  63,  64,  65,  66,  67,  68,  69,  70,  71,
   72,  73,  75,  76,  77,  78,  79,  80,  82,  83,  84,  85,  87,  88,  89,  90,
   92,  93,  94,  96,  97,  98, 100, 101, 103, 104, 105, 107, 108, 110, 111, 113,
  114, 116, 117, 119, 120, 122, 123, 125, 127, 128, 130, 131, 133, 135, 136, 138,
  140, 141, 143, 145, 147, 148, 150, 152, 154, 155, 157, 159, 161, 163, 165, 166,
  168, 170, 172, 174, 176, 178, 180, 182, 184, 186, 188, 190, 192, 194, 196, 198,
  200, 202, 204, 206, 209, 211, 213, 215, 217, 220, 222, 224, 226, 229, 231, 255
};
#endif

/**
 * @brief  初始化WS2812驱动
 */
void WS2812_Init(TIM_HandleTypeDef *htim, uint32_t channel)
{
    ws2812_htim = htim;
    ws2812_channel = channel;
    
    memset(led_data, 0, sizeof(led_data));
    memset(dma_buffer, 0, sizeof(dma_buffer));
}

/**
 * @brief  设置单个LED颜色
 */
void WS2812_SetPixel(uint16_t index, uint8_t r, uint8_t g, uint8_t b)
{
    if (index >= WS2812_NUM_LEDS) return;
    
#if WS2812_USE_GAMMA
    led_data[index * 3 + 0] = gamma_table[r];
    led_data[index * 3 + 1] = gamma_table[g];
    led_data[index * 3 + 2] = gamma_table[b];
#else
    led_data[index * 3 + 0] = r;
    led_data[index * 3 + 1] = g;
    led_data[index * 3 + 2] = b;
#endif
}

/**
 * @brief  设置所有LED为同一颜色
 */
void WS2812_SetAll(uint8_t r, uint8_t g, uint8_t b)
{
    for (uint16_t i = 0; i < WS2812_NUM_LEDS; i++) {
        WS2812_SetPixel(i, r, g, b);
    }
}

/**
 * @brief  清除所有LED (关闭)
 */
void WS2812_Clear(void)
{
    memset(led_data, 0, sizeof(led_data));
}

/**
 * @brief  将RGB数据转换为PWM数据并发送
 */
void WS2812_Update(void)
{
    if (dma_busy) return;
    
    uint16_t *p = dma_buffer;
    
    /* 转换每个LED的数据 (GRB顺序) */
    for (uint16_t i = 0; i < WS2812_NUM_LEDS; i++) {
        uint8_t g = led_data[i * 3 + 1];
        uint8_t r = led_data[i * 3 + 0];
        uint8_t b = led_data[i * 3 + 2];
        
        /* Green */
        for (int8_t bit = 7; bit >= 0; bit--) {
            *p++ = (g & (1 << bit)) ? WS2812_HI : WS2812_LO;
        }
        /* Red */
        for (int8_t bit = 7; bit >= 0; bit--) {
            *p++ = (r & (1 << bit)) ? WS2812_HI : WS2812_LO;
        }
        /* Blue */
        for (int8_t bit = 7; bit >= 0; bit--) {
            *p++ = (b & (1 << bit)) ? WS2812_HI : WS2812_LO;
        }
    }
    
    /* 复位时间 (低电平) */
    for (uint16_t i = 0; i < RESET_SLOTS; i++) {
        *p++ = 0;
    }
    
    dma_busy = 1;
    HAL_TIM_PWM_Start_DMA(ws2812_htim, ws2812_channel, (uint32_t *)dma_buffer, DMA_BUF_SIZE);
}

/**
 * @brief  检查DMA是否正在传输
 */
uint8_t WS2812_IsBusy(void)
{
    return dma_busy;
}

/**
 * @brief  DMA传输完成回调
 */
void WS2812_DMACompleteCallback(void)
{
    HAL_TIM_PWM_Stop_DMA(ws2812_htim, ws2812_channel);
    dma_busy = 0;
}
