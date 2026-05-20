#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_camera.h"
#include "esp_http_client.h"

#include "wifi_manager.h"  // Wi-Fi 매니저 헤더 포함
#include "camera_manager.h"  // 카메라 매니저 헤더 포함
#include "sdkconfig.h"

static const char *TAG = "SSCCam_Main";

#define WIFI_SSID      CONFIG_WIFI_SSID
#define WIFI_PASS      CONFIG_WIFI_PASSWORD
#define SERVER_URL     CONFIG_SERVER_URL
#define COMMAND_URL    CONFIG_COMMAND_URL
#define MAXIMUM_RETRY  5

// 서버로 이미지를 전송하는 함수
static esp_err_t send_image_to_server(camera_fb_t *fb) {
    esp_http_client_config_t config = {
        .url = SERVER_URL,
        .method = HTTP_METHOD_POST,
        .timeout_ms = 5000, 
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    const char *boundary = "----ESP32BoundarySSCCounter";
    char content_type[64];
    snprintf(content_type, sizeof(content_type), "multipart/form-data; boundary=%s", boundary);
    esp_http_client_set_header(client, "Content-Type", content_type);

    const char *body_start = 
        "------ESP32BoundarySSCCounter\r\n"
        "Content-Disposition: form-data; name=\"file\"; filename=\"esp32_cam.jpg\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n";
    
    const char *body_end = "\r\n------ESP32BoundarySSCCounter--\r\n";

    int content_length = strlen(body_start) + fb->len + strlen(body_end);
    esp_http_client_open(client, content_length);
    esp_http_client_write(client, body_start, strlen(body_start));
    esp_http_client_write(client, (const char *)fb->buf, fb->len);
    esp_http_client_write(client, body_end, strlen(body_end));
    esp_http_client_fetch_headers(client);

    int status_code = esp_http_client_get_status_code(client);
    ESP_LOGI(TAG, "HTTP Status Code: %d", status_code);
    esp_http_client_cleanup(client);

    return (status_code == 200) ? ESP_OK : ESP_FAIL;
}

void app_main(void) {
    // 1. NVS 초기화
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 2. Wi-Fi 연결 수행
    ESP_LOGI(TAG, "Connecting to Wi-Fi...");
    if (wifi_init_sta(WIFI_SSID, WIFI_PASS, MAXIMUM_RETRY) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to connect to Wi-Fi.");
        return;
    }

    // 3. 카메라 초기화
    if (camera_manager_init() != ESP_OK) {
        ESP_LOGE(TAG, "Cannot initialize camera. Halting system.");
        return;
    }

    ESP_LOGI(TAG, "System ready. Starting 30-second interval capture.");

    // 4. 무한 루프 캡처 및 전송
    while (1) {
        ESP_LOGI(TAG, "Capturing image...");
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) {
            ESP_LOGE(TAG, "Camera capture failed!");
        } else {
            ESP_LOGI(TAG, "Sending image to server... (Size: %zu bytes)", fb->len);
            send_image_to_server(fb);
            esp_camera_fb_return(fb);
        }
        vTaskDelay(pdMS_TO_TICKS(30000));
        // esp_http_client_config_t cmd_config = {
        //     .url = COMMAND_URL,
        //     .method = HTTP_METHOD_GET,
        //     .timeout_ms = 2000,
        // };
        // esp_http_client_handle_t cmd_client = esp_http_client_init(&cmd_config);
        
        // char response_buffer[128] = {0};
        // esp_err_t err = esp_http_client_open(cmd_client, 0);
        // if (err == ESP_OK) {
        //     esp_http_client_fetch_headers(cmd_client);
        //     esp_http_client_read(cmd_client, response_buffer, sizeof(response_buffer));
            
        //     // 서버 응답에 "capture"라는 단어가 있으면 사진 촬영 및 전송!
        //     if (strstr(response_buffer, "capture") != NULL) {
        //         ESP_LOGI(TAG, "Capture command received from server!");
        //         camera_fb_t *fb = esp_camera_fb_get();
        //         if (fb) {
        //             send_image_to_server(fb); // 기존 사진 전송 함수
        //             esp_camera_fb_return(fb);
        //         }
        //     }
        // }
        // esp_http_client_cleanup(cmd_client);

        // // 30초 대기 대신 3초만 대기하고 다시 명령 확인
        // vTaskDelay(pdMS_TO_TICKS(3000));
    }
}