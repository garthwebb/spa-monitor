#include <InfluxDBHandler.h>

extern Logger *LOGGER;

InfluxDBHandler::InfluxDBHandler(const String &url, const String &db) {
    LOGGER->log("Initializing InfluxDBHandler");
    Serial.println("Initialziing InfluxDB: ");
 

    _client = new InfluxDBClient(url, db);
    _point = new Point("temperature");

    if (_client->validateConnection()) {
        Serial.println("\tConnected to InfluxDB: " + _client->getServerUrl());
        LOGGER->log("Connected to InfluxDB at " + _client->getServerUrl());
    } else {
        Serial.println("\tInfluxDB connection failed: " + _client->getLastErrorMessage());
        LOGGER->log_error("InfluxDB connection failed: " + _client->getLastErrorMessage());
    }

    if (_log_events) {
        LOGGER->log("Logging events to InfluxDB is enabled");
    }
}

bool InfluxDBHandler::add_reading(Sensor *sensor) {
    // Clear fields for reusing the point. Tags will remain untouched
    _point->clearTags();
    _point->clearFields();

    // Store temp
    _point->addTag("address", sensor->get_address_string());
    _point->addField("value", sensor->temp);

    if (!_log_events) {
        return true;
    }

    if (!_client->writePoint(*_point)) {
        LOGGER->log_error("Failed to add reading: " + last_error());
        return false;
    }

    return true;
}

String InfluxDBHandler::last_error() {
    return _client->getLastErrorMessage();
}

void InfluxDBHandler::enable_logging() {
    _log_events = true;
}

void InfluxDBHandler::disable_logging() {
    _log_events = false;
}