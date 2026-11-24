#include "esp_camera.h"
#include <WiFi.h>

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"
#define port 5005

const char *ssid_STA = "ENGR100-400";
const char *password_STA = "notapwd777";

IPAddress local_IP(192, 168, 50, 207);
IPAddress gateway(192, 168, 50, 1);
IPAddress subnet(255, 255, 255, 0);

WiFiServer server(port);
WiFiClient client;
bool client_active = false;

void startCameraServer();
extern volatile int capture_failures;

#define MAX_CAPTURE_FAILURES 3

const char *reset_reason_name() {
  switch (esp_reset_reason()) {
    case ESP_RST_POWERON: return "POWER_ON";
    case ESP_RST_SW: return "SOFTWARE_RESTART";
    case ESP_RST_PANIC: return "CRASH";
    case ESP_RST_INT_WDT: return "INTERRUPT_WATCHDOG";
    case ESP_RST_TASK_WDT: return "TASK_WATCHDOG";
    case ESP_RST_WDT: return "WATCHDOG";
    case ESP_RST_BROWNOUT: return "BROWNOUT";
    case ESP_RST_DEEPSLEEP: return "DEEP_SLEEP";
    case ESP_RST_EXT: return "EXTERNAL_RESET";
    default: return "UNKNOWN";
  }
}

void cameraServerSetup() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 18;

  if (psramFound()) {
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  }
  else {
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x. Restarting in 2s...\n", err);
    delay(2000);
    ESP.restart();
  }
  Serial.println("Camera initialized successfully.");

  sensor_t * s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_QVGA);
  s->set_vflip(s, 0);
  s->set_hmirror(s, 0);
}

void WiFiSetup() {
  Serial.println("Connecting as station with static IP...");
  WiFi.disconnect();
  WiFi.mode(WIFI_STA);
  Serial.println(WiFi.config(local_IP, gateway, subnet) ? "Ready" : "Failed!");
  WiFi.begin(ssid_STA, password_STA);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected.");
  Serial.print("Station IP address = ");
  Serial.println(WiFi.localIP());

  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  server.begin(port);
  server.setNoDelay(true);
}

void forward_to_nano(String line) {
  line.trim();
  if (line == "STOP" || line.indexOf(',') > 0) {
    Serial.println(line);
  }
}

void setup() {
  Serial.begin(115200);

  cameraServerSetup();
  WiFiSetup();

  Serial.println("Starting camera server...");
  startCameraServer();
  Serial.println("Camera server started.");
}

void loop() {
  if (capture_failures >= MAX_CAPTURE_FAILURES) {
    Serial.println("STOP");
    Serial.println("Camera stopped giving frames. Restarting...");
    delay(500);
    ESP.restart();
  }

  WiFiClient incoming = server.available();
  if (incoming) {
    client.stop();
    client = incoming;
    client.setNoDelay(true);
    client.setTimeout(100);
    client_active = true;
    Serial.println("STOP");
    client.printf("INFO last_reset=%s uptime=%lus psram=%s free_heap=%u\n",
                  reset_reason_name(), millis() / 1000, psramFound() ? "yes" : "no", ESP.getFreeHeap());
  }

  if (client_active && !client.connected()) {
    client.stop();
    client_active = false;
    Serial.println("STOP");
  }

  while (client_active && client.available()) {
    forward_to_nano(client.readStringUntil('\n'));
  }
}
