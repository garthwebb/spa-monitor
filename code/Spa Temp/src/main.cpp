#include "main.h"

#include <esp_task_wdt.h>
#include <esp_system.h>

#include "Logger.h"
#include "WirelessControl.h"
#include "SensorHandler.h"
#include "InfluxDBHandler.h"

Logger *LOGGER;
SensorHandler *SENSOR_HANDLER;
InfluxDBHandler *INFLUX;

long last_heartbeat_ms = millis();

void check_for_reset() {
  esp_reset_reason_t reason = esp_reset_reason();

  // Log the reset reason, or nothing if no reset was detected
  switch(reason) {
      case ESP_RST_UNKNOWN:
          LOGGER->log_error("Reset reason: Unknown");
          break;
      case ESP_RST_POWERON:
          LOGGER->log_error("Reset reason: Power on");
          break;
      case ESP_RST_EXT:
          LOGGER->log_error("Reset reason: External pin");
          break;
      case ESP_RST_SW:    
          LOGGER->log_error("Reset reason: Software reset");
          break;
      case ESP_RST_PANIC:
          LOGGER->log_error("Reset reason: Panic");
          break;
      case ESP_RST_INT_WDT:
          LOGGER->log_error("Reset reason: Interrupt watchdog");
          break;
      case ESP_RST_TASK_WDT:
          LOGGER->log_error("Reset reason: Task watchdog");
          break;
      case ESP_RST_WDT:
          LOGGER->log_error("Reset reason: Other watchdog");
          break;
      case ESP_RST_DEEPSLEEP:
          LOGGER->log_error("Reset reason: Deep sleep");
          break;
      case ESP_RST_BROWNOUT:
          LOGGER->log_error("Reset reason: Brownout");
          break;
      case ESP_RST_SDIO:
          LOGGER->log_error("Reset reason: SDIO");
          break;
  }
}

void setup() {
  // start serial port
  Serial.begin(115200);
  Serial.println("Hottub monitor starting up ...");

  LOGGER = new Logger();

  WirelessControl::init_wifi(WIFI_SSID, WIFI_PASSWORD);

  LOGGER->log("Hottub monitor power cycled, starting up.  Sampling every " + String(SAMPLE_TIME_PERIOD_SEC) + " seconds.");

  SENSOR_HANDLER = new SensorHandler();

  INFLUX = new InfluxDBHandler(INFLUXDB_URL, INFLUXDB_DB);
  if (LOG_TO_INFLUX) {
    INFLUX->enable_logging();
  } else {
      INFLUX->disable_logging();
  }

  // Initialize the Watchdog Timer
  esp_task_wdt_init(WDT_TIMEOUT_SEC, true);
  // Add the current task to the Watchdog Timer, (the behavior when the task handler == NULL)
  esp_task_wdt_add(NULL);

  // Check for a reset from some prior run
  check_for_reset();
}

void loop() {
  SENSOR_HANDLER->load_readings();

  for (auto &sensor : SENSOR_HANDLER->sensors) {
    INFLUX->add_reading(&sensor);
  }

  if (millis() > last_heartbeat_ms + HEARTBEAT_PERIOD_MS) {
    LOGGER->log("Hottub monitor hearbeat");
    last_heartbeat_ms = millis();

    esp_task_wdt_reset();
  }

  sleep(SAMPLE_TIME_PERIOD_SEC);
}
