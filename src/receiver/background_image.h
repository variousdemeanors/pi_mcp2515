#ifndef BACKGROUND_IMAGE_H
#define BACKGROUND_IMAGE_H

#ifdef __has_include
#if __has_include("lvgl.h")
#ifndef LV_LVGL_H_INCLUDE_SIMPLE
#define LV_LVGL_H_INCLUDE_SIMPLE
#endif
#endif
#endif

#if defined(LV_LVGL_H_INCLUDE_SIMPLE)
#include "lvgl.h"
#else
#include "lvgl/lvgl.h"
#endif

#include "FS.h"
#include "SPIFFS.h"
#include "SPI.h"

// SPIFFS background image loader
class BackgroundImageLoader
{
private:
    static lv_img_dsc_t *background_img;
    static uint8_t *image_data;
    static bool spiffs_initialized;

public:
    // Initialize SPIFFS for background loading
    static bool initSPIFFS();

    // Load background image from SPIFFS
    static lv_img_dsc_t *loadBackground(const char *filename = "/images/automotive_bg.rgb565");

    // Free loaded background memory
    static void freeBackground();

    // Check if background is loaded
    static bool isLoaded() { return background_img != nullptr; }

    // Get the loaded background image descriptor
    static lv_img_dsc_t *getBackground() { return background_img; }
};

// Static member declarations
lv_img_dsc_t *BackgroundImageLoader::background_img = nullptr;
uint8_t *BackgroundImageLoader::image_data = nullptr;
bool BackgroundImageLoader::spiffs_initialized = false;

bool BackgroundImageLoader::initSPIFFS()
{
    if (spiffs_initialized)
        return true;

    // SPIFFS should already be initialized by main setup
    spiffs_initialized = true;
    return true;
}

lv_img_dsc_t *BackgroundImageLoader::loadBackground(const char *filename)
{
    if (!initSPIFFS())
    {
        Serial.println("SPIFFS not available for background loading");
        return nullptr;
    }

    // Free any existing background
    freeBackground();

    // Check if file exists
    if (!SPIFFS.exists(filename))
    {
        Serial.printf("Background file %s not found in SPIFFS\n", filename);
        return nullptr;
    }

    File file = SPIFFS.open(filename, "r");
    if (!file)
    {
        Serial.printf("Failed to open background file %s\n", filename);
        return nullptr;
    }

    size_t fileSize = file.size();
    Serial.printf("Loading background image: %s (%d bytes)\n", filename, fileSize);

    // Allocate memory for image data
    image_data = (uint8_t *)malloc(fileSize);
    if (!image_data)
    {
        Serial.println("Failed to allocate memory for background image");
        file.close();
        return nullptr;
    }

    // Read image data
    size_t bytesRead = file.read(image_data, fileSize);
    file.close();

    if (bytesRead != fileSize)
    {
        Serial.printf("Failed to read complete image file. Read %d of %d bytes\n", bytesRead, fileSize);
        free(image_data);
        image_data = nullptr;
        return nullptr;
    }

    // Create LVGL image descriptor
    background_img = (lv_img_dsc_t *)malloc(sizeof(lv_img_dsc_t));
    if (!background_img)
    {
        Serial.println("Failed to allocate memory for image descriptor");
        free(image_data);
        image_data = nullptr;
        return nullptr;
    }

    // Set up image descriptor for RGB565 format
    background_img->header.cf = LV_IMG_CF_TRUE_COLOR;
    background_img->header.always_zero = 0;
    background_img->header.reserved = 0;
    background_img->header.w = 320; // Landscape orientation
    background_img->header.h = 240;
    background_img->data_size = fileSize;
    background_img->data = image_data;

    Serial.println("Background image loaded successfully from SPIFFS");
    return background_img;
}

void BackgroundImageLoader::freeBackground()
{
    if (image_data)
    {
        free(image_data);
        image_data = nullptr;
    }
    if (background_img)
    {
        free(background_img);
        background_img = nullptr;
    }
}

#endif // BACKGROUND_IMAGE_H