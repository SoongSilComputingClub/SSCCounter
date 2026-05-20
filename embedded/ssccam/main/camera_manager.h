#ifndef CAMERA_MANAGER_H
#define CAMERA_MANAGER_H

#include "esp_err.h"
#include "esp_camera.h"

/**
 * @brief ESP32-CAM (AI-Thinker) 카메라 모듈을 초기화합니다.
 * @return esp_err_t 초기화 성공 시 ESP_OK, 실패 시 ESP_FAIL
 */

esp_err_t camera_manager_init(void);

#endif // CAMERA_MANAGER_H