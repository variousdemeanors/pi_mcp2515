/**
 * @file lv_conf.h
 * Minimal Configuration file for LVGL v8.3 - ST7789 Display
 */

#ifndef LV_CONF_H
#define LV_CONF_H

#include <stdint.h>

/*====================
   COLOR SETTINGS
 *====================*/

/*Color depth: 16 (RGB565) for ST7789*/
#define LV_COLOR_DEPTH 16

/*Swap the 2 bytes of RGB565 color. Usually 0 for ST7789*/
#define LV_COLOR_16_SWAP 0

/*Disable transparency for simplicity*/
#define LV_COLOR_SCREEN_TRANSP 0

/*====================
   MEMORY SETTINGS
 *====================*/

/*Use built-in memory management*/
#define LV_MEM_CUSTOM 0
#if LV_MEM_CUSTOM == 0
/*Reduced memory size for minimal setup - 16KB should be enough for basic UI*/
#define LV_MEM_SIZE (16U * 1024U) /*[bytes]*/
#define LV_MEM_ADR 0              /*0: unused*/
#else
#define LV_MEM_CUSTOM_INCLUDE <stdlib.h>
#define LV_MEM_CUSTOM_ALLOC malloc
#define LV_MEM_CUSTOM_FREE free
#define LV_MEM_CUSTOM_REALLOC realloc
#endif

/*Reduced buffer count for minimal setup*/
#define LV_MEM_BUF_MAX_NUM 8

/*Use standard memcpy/memset*/
#define LV_MEMCPY_MEMSET_STD 0

/*====================
   HAL SETTINGS
 *====================*/

/*Default display refresh period*/
#define LV_DISP_DEF_REFR_PERIOD 30 /*[ms]*/

/*Input device read period*/
#define LV_INDEV_DEF_READ_PERIOD 30 /*[ms]*/

/*Use Arduino millis() for timing*/
#define LV_TICK_CUSTOM 1
#if LV_TICK_CUSTOM
#define LV_TICK_CUSTOM_INCLUDE <Arduino.h>
#define LV_TICK_CUSTOM_SYS_TIME_EXPR (millis())
#endif

/*Default DPI*/
#define LV_DPI_DEF 130 /*[px/inch]*/

/*====================
 * FEATURE CONFIGURATION
 *====================*/

/*Disable complex drawing for minimal setup*/
#define LV_DRAW_COMPLEX 0

/*Disable image cache*/
#define LV_IMG_CACHE_DEF_SIZE 0

/*Minimal gradient stops*/
#define LV_GRADIENT_MAX_STOPS 2

/*Disable all GPU acceleration*/
#define LV_USE_GPU_STM32_DMA2D 0
#define LV_USE_GPU_NXP_PXP 0
#define LV_USE_GPU_NXP_VG_LITE 0

/*Disable logging for minimal setup*/
#define LV_USE_LOG 0

/*Basic asserts only*/
#define LV_USE_ASSERT_NULL 1
#define LV_USE_ASSERT_MALLOC 1
#define LV_USE_ASSERT_STYLE 0
#define LV_USE_ASSERT_MEM_INTEGRITY 0
#define LV_USE_ASSERT_OBJ 0

/*Halt on assert*/
#define LV_ASSERT_HANDLER_INCLUDE <stdint.h>
#define LV_ASSERT_HANDLER \
    while (1)             \
        ;

/*Disable performance monitoring*/
#define LV_USE_PERF_MONITOR 0
#define LV_USE_MEM_MONITOR 0
#define LV_USE_REFR_DEBUG 0

/*Use built-in sprintf*/
#define LV_SPRINTF_CUSTOM 0
#if LV_SPRINTF_CUSTOM == 0
#define LV_SPRINTF_USE_FLOAT 0
#endif

/*Enable user data*/
#define LV_USE_USER_DATA 1

/*Disable garbage collection*/
#define LV_ENABLE_GC 0

/*=====================
 *  COMPILER SETTINGS
 *====================*/

/*Standard settings*/
#define LV_BIG_ENDIAN_SYSTEM 0
#define LV_ATTRIBUTE_TICK_INC
#define LV_ATTRIBUTE_TIMER_HANDLER
#define LV_ATTRIBUTE_FLUSH_READY
#define LV_ATTRIBUTE_MEM_ALIGN_SIZE 1
#define LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_LARGE_CONST
#define LV_ATTRIBUTE_LARGE_RAM_ARRAY
#define LV_ATTRIBUTE_FAST_MEM
#define LV_ATTRIBUTE_DMA
#define LV_EXPORT_CONST_INT(int_value) struct _silence_gcc_warning
#define LV_USE_LARGE_COORD 0

/*==================
 *   FONT USAGE
 *=================*/

/*Enable only basic Montserrat fonts*/
#define LV_FONT_MONTSERRAT_8 0
#define LV_FONT_MONTSERRAT_10 0
#define LV_FONT_MONTSERRAT_12 0
#define LV_FONT_MONTSERRAT_14 1 /*Default font*/
#define LV_FONT_MONTSERRAT_16 0
#define LV_FONT_MONTSERRAT_18 0
#define LV_FONT_MONTSERRAT_20 0
#define LV_FONT_MONTSERRAT_22 0
#define LV_FONT_MONTSERRAT_24 0
#define LV_FONT_MONTSERRAT_26 0
#define LV_FONT_MONTSERRAT_28 0
#define LV_FONT_MONTSERRAT_30 0
#define LV_FONT_MONTSERRAT_32 0
#define LV_FONT_MONTSERRAT_34 0
#define LV_FONT_MONTSERRAT_36 0
#define LV_FONT_MONTSERRAT_38 0
#define LV_FONT_MONTSERRAT_40 0
#define LV_FONT_MONTSERRAT_42 0
#define LV_FONT_MONTSERRAT_44 0
#define LV_FONT_MONTSERRAT_46 0
#define LV_FONT_MONTSERRAT_48 0

/*Disable special fonts*/
#define LV_FONT_MONTSERRAT_12_SUBPX 0
#define LV_FONT_MONTSERRAT_28_COMPRESSED 0
#define LV_FONT_DEJAVU_16_PERSIAN_HEBREW 0
#define LV_FONT_SIMSUN_16_CJK 0
#define LV_FONT_UNSCII_8 0
#define LV_FONT_UNSCII_16 0

/*No custom fonts*/
#define LV_FONT_CUSTOM_DECLARE

/*Default font*/
#define LV_FONT_DEFAULT &lv_font_montserrat_14

/*Disable advanced font features*/
#define LV_FONT_FMT_TXT_LARGE 0
#define LV_USE_FONT_COMPRESSED 0
#define LV_USE_FONT_SUBPX 0

/*=================
 *  TEXT SETTINGS
 *=================*/

#define LV_TXT_ENC LV_TXT_ENC_UTF8
#define LV_TXT_BREAK_CHARS " ,.;:-_"
#define LV_TXT_LINE_BREAK_LONG_LEN 0
#define LV_TXT_LINE_BREAK_LONG_PRE_MIN_LEN 3
#define LV_TXT_LINE_BREAK_LONG_POST_MIN_LEN 3
#define LV_TXT_COLOR_CMD "#"
#define LV_USE_BIDI 0
#define LV_USE_ARABIC_PERSIAN_CHARS 0

/*==================
 *  WIDGET USAGE
 *================*/

/*Enable only essential widgets for minimal setup*/
#define LV_USE_ARC 0       /*Disable for now*/
#define LV_USE_BAR 1       /*Basic progress bar*/
#define LV_USE_BTN 1       /*Basic button*/
#define LV_USE_BTNMATRIX 0 /*Disable for minimal setup*/
#define LV_USE_CANVAS 0    /*Disable for minimal setup*/
#define LV_USE_CHECKBOX 0  /*Disable for minimal setup*/
#define LV_USE_DROPDOWN 0  /*Disable for minimal setup*/
#define LV_USE_IMG 1       /*Basic image support*/
#define LV_USE_LABEL 1     /*Essential for text*/
#define LV_USE_LINE 0      /*Disable for minimal setup*/
#define LV_USE_METER 0     /*Disable for now - we'll add back later*/
#define LV_USE_MSGBOX 0    /*Disable for minimal setup*/
#define LV_USE_ROLLER 0    /*Disable for minimal setup*/
#define LV_USE_SLIDER 0    /*Disable for minimal setup*/
#define LV_USE_SPAN 0      /*Disable for minimal setup*/
#define LV_USE_SPINBOX 0   /*Disable for minimal setup*/
#define LV_USE_SPINNER 0   /*Disable for minimal setup*/
#define LV_USE_SWITCH 0    /*Disable for minimal setup*/
#define LV_USE_TEXTAREA 0  /*Disable for minimal setup*/
#define LV_USE_TABLE 0     /*Disable for minimal setup*/
#define LV_USE_TABVIEW 0   /*Disable for minimal setup*/
#define LV_USE_TILEVIEW 0  /*Disable for minimal setup*/
#define LV_USE_WIN 0       /*Disable for minimal setup*/

/* Explicitly disable keyboard to avoid pulling in btnmatrix/textarea deps */
#define LV_USE_KEYBOARD 0

/*==================
 * THEME USAGE
 *================*/

/*Use simple default theme*/
#define LV_USE_THEME_DEFAULT 1
#if LV_USE_THEME_DEFAULT
#define LV_THEME_DEFAULT_DARK 0            /*Light mode*/
#define LV_THEME_DEFAULT_GROW 0            /*No grow animation*/
#define LV_THEME_DEFAULT_TRANSITION_TIME 0 /*No transitions*/
#endif

/*Disable other themes*/
#define LV_USE_THEME_BASIC 0
#define LV_USE_THEME_MONO 0

/*==================
 * LAYOUTS
 *================*/

/*Enable basic flex layout*/
#define LV_USE_FLEX 1
/*Disable grid layout for minimal setup*/
#define LV_USE_GRID 0

/*==================
 * 3RD PARTS LIBRARIES
 *================*/

/*Disable all file system and image decoders for minimal setup*/
#define LV_USE_FS_STDIO 0
#define LV_USE_FS_POSIX 0
#define LV_USE_FS_WIN32 0
#define LV_USE_FS_FATFS 0
#define LV_USE_PNG 0
#define LV_USE_BMP 0
#define LV_USE_SJPG 0
#define LV_USE_GIF 0
#define LV_USE_QRCODE 0
#define LV_USE_FREETYPE 0
#define LV_USE_RLOTTIE 0
#define LV_USE_FFMPEG 0

/*==================
 * OTHERS
 *================*/

/*Disable all advanced features for minimal setup*/
#define LV_USE_SNAPSHOT 0
#define LV_USE_MONKEY 0
#define LV_USE_GRIDNAV 0
#define LV_USE_FRAGMENT 0
#define LV_USE_IMGFONT 0
#define LV_USE_MSG 0
#define LV_USE_IME_PINYIN 0

/*==================
 * EXAMPLES
 *================*/

/*Disable all examples and demos*/
#define LV_BUILD_EXAMPLES 0
#define LV_USE_DEMO_WIDGETS 0
#define LV_USE_DEMO_KEYPAD_AND_ENCODER 0
#define LV_USE_DEMO_BENCHMARK 0
#define LV_USE_DEMO_STRESS 0
#define LV_USE_DEMO_MUSIC 0

/*--END OF LV_CONF_H--*/

#endif /*LV_CONF_H*/