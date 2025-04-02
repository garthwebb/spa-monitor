#ifndef INFLUXDBHANDLER_H
#define INFLUXDBHANDLER_H

#include <Arduino.h>
#include <InfluxDbClient.h>
#include <InfluxDbCloud.h>

#include "Logger.h"
#include "Sensor.h"

class InfluxDBHandler {
    private:
    InfluxDBClient *_client;
    bool _log_events = true;
    Point *_point;

    public:
    InfluxDBHandler(const String &serverUrl, const String &db);

    bool add_reading(Sensor *sensor);

    String last_error();
    void enable_logging();
    void disable_logging();
};

#endif