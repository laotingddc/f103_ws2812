/**
 * @file    ws2812.h
 * @brief   WS2812 LED驱动 (HAL库版本)
 */
#ifndef __WS2812_H__
#define __WS2812_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include "tim.h"

/* 配置参数 */
#define WS2812_NUM_LEDS     (96)     // LED数量
#define WS2812_USE_GAMMA    1       // 是否使用gamma校正

/* 时序参数 (基于72MHz, Period=89) */
#define WS2812_HI           58      // 逻辑1的高电平时间 (~0.8us)
#define WS2812_LO           29      // 逻辑0的高电平时间 (~0.4us)

/* 函数声明 */
void WS2812_Init(TIM_HandleTypeDef *htim, uint32_t channel);
void WS2812_SetPixel(uint16_t index, uint8_t r, uint8_t g, uint8_t b);
void WS2812_SetAll(uint8_t r, uint8_t g, uint8_t b);
void WS2812_Clear(void);
void WS2812_Update(void);
uint8_t WS2812_IsBusy(void);

/* DMA传输完成回调 (需要在stm32f1xx_it.c中调用) */
void WS2812_DMACompleteCallback(void);

#ifdef __cplusplus
}
#endif

#endif /* __WS2812_H__ */
