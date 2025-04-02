#include "main.h"
#include "SensorHandler.h"

SensorHandler *SENSOR_HANDLER;

void setup() {
  // start serial port
  Serial.begin(115200);
  Serial.println("Testing OneWire bus on pin " + String(ONE_WIRE_BUS));
  SENSOR_HANDLER = new SensorHandler();
}

void loop() {
  SENSOR_HANDLER->load_readings();

  sleep(2);
}
