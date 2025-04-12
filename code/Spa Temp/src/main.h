#ifndef MAIN_H
#define MAIN_H

#include <Arduino.h>
#include "wifi-info.h"


#define HOSTNAME "hottub-esp32"

// Syslog server connection info
#define SYSLOG_SERVER "tigerbackup.local"
#define SYSLOG_PORT 514
#define APP_NAME "hottub-monitor"

//-- Influx DB
//#define INFLUXDB_URL "http://tiger-pi.local:8086"
#define INFLUXDB_URL "http://192.168.3.88:8086"
#define INFLUXDB_DB "hottub_monitor"
#define TELEMETRY_DB "telemetry"

// Quickly enable/disable infux logging
#define LOG_TO_INFLUX true
#define LOG_TELEMETRY true

#define ONE_WIRE_BUS D8
#define ONE_WIRE_SETTLE_MILLIS 500

#define SAMPLE_TIME_PERIOD_SEC 1*60
#define SAMPLE_TIME_PERIOD_MS SAMPLE_TIME_PERIOD_SEC*1000

#define HEARTBEAT_PERIOD_SEC 10*60
#define HEARTBEAT_PERIOD_MS HEARTBEAT_PERIOD_SEC*1000

// Set a short watchdog timeout
#define WDT_TIMEOUT_SEC 20

#endif
