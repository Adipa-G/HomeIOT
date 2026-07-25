from machine import ADC

# The Pico's onboard temperature sensor is wired to ADC channel 4.
_sensor = ADC(4)
_CONVERSION_FACTOR = 3.3 / 65535


def run(ctx):
    raw = _sensor.read_u16()
    voltage = raw * _CONVERSION_FACTOR
    # Formula from the RP2040 datasheet.
    temp_celsius = 27 - (voltage - 0.706) / 0.001721
    return {
        "raw_value": raw,
        "temp_celsius": round(temp_celsius, 1),
    }
