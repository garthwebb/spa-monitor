#include "SensorHandler.h"

SensorHandler::SensorHandler(): _one_wire(ONE_WIRE_BUS), _sensor_interface(&_one_wire) {
	// Start up the library
	_sensor_interface.begin();

    byte address[8];
    while (_one_wire.search(address)) {
        Serial.print("Found device with address: ");
		Serial.println(Sensor::byteArrayToString(address));

		sensors.push_back(Sensor(address));
    }

	// Reset search for next loop
    _one_wire.reset_search();

	Serial.printf("Found %d devices.\n", sensors.size());
}

void SensorHandler::load_readings() {
	_sensor_interface.requestTemperatures();
	delay(ONE_WIRE_SETTLE_MILLIS);

	for (auto &sensor : sensors) {
		sensor.temp = _sensor_interface.getTempC(sensor.address);
		Serial.printf("Sensor %s: %f\n", sensor.get_address_string().c_str(), sensor.temp);
	}
}
