#ifndef SENSORHANDLER_H
#define SENSORHANDLER_H

#include <OneWire.h>
#include <DallasTemperature.h>
#include <vector>

#include "main.h"
#include "Logger.h"
#include "Sensor.h"

class SensorHandler {
    public:
	std::vector<Sensor> sensors;

    SensorHandler();
	void load_readings();

    private:
	OneWire _one_wire;
	DallasTemperature _sensor_interface;
};

#endif