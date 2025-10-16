file(GLOB_RECURSE SOURCES   ./*.c
							)

idf_component_register(SRCS ${SOURCES}
                   INCLUDE_DIRS
                                .
                                ../lvgl_esp32_drivers/lvgl_touch
                    REQUIRES  lvgl
                              lvgl_esp32_drivers
                              )
