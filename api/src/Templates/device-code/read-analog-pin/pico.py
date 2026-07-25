from machine import ADC, Pin

# Pico analog-capable inputs are GPIO26, 27, 28 (ADC0-ADC2).
PIN_NUMBER = 26

_adc = ADC(Pin(PIN_NUMBER))


def run(ctx):
    raw = _adc.read_u16()  # 0-65535
    voltage = raw / 65535 * 3.3
    return {
        "pin": PIN_NUMBER,
        "raw_value": raw,
        "voltage": round(voltage, 3),
    }
