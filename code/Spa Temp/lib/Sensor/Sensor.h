#ifndef SENSOR_H
#define SENSOR_H

#include "main.h"
#include "Logger.h"

class Sensor {
    public:
	float temp;
	byte address[8];

    Sensor(byte addr[8]);
	float read_temp();
	String get_address_string() const;

	static String byteArrayToString(const byte address[8]);

    private:

};

#endif