#include "Sensor.h"

Sensor::Sensor(byte addr[8]) {
	for (int i = 0; i < 8; i++) {
		address[i] = addr[i];
	}
}

String Sensor::get_address_string() const {
	return Sensor::byteArrayToString(address);
}

String Sensor::byteArrayToString(const byte address[8]) {
    String address_string = "";
    for (int i = 0; i < 8; i++) {
        if (address[i] < 16) address_string += "0";
        address_string += String(address[i], HEX);
    }
    return address_string;
}