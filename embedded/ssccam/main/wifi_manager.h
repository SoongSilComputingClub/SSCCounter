#ifndef WIFI_MANAGE_H
#define WIFI_MANAGE_H

#include "esp_err.h"

/**
 * @brief 지정된 SSID와 Password를 사용하여 Wi-Fi STA 모드로 연결을 시도합니다.
 * @param ssid 연결할 Wi-Fi 이름
 * @param pass 연결할 Wi-Fi 비밀번호
 * @param max_retry 연결 실패 시 최대 재시도 횟수
 * @return esp_err_t 연결 성공 시 ESP_OK, 실패 시 ESP_FAIL
 */
esp_err_t wifi_init_sta(const char *ssid, const char *pass, int max_retry);

#endif // WIFI_MANAGE_H