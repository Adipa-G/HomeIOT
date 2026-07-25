from machine import ADC, Pin

# GPIO34 is one of the ADC1-capable, input-only pins on most ESP32 boards.
PIN_NUMBER = 34

_adc = ADC(Pin(PIN_NUMBER))
_adc.atten(ADC.ATTN_11DB)  # allow the full 0-3.6V input range


def run(ctx):
    raw = _adc.read_u16()  # 0-65535
    voltage = raw / 65535 * 3.3
    return {
        "pin": PIN_NUMBER,
        "raw_value": raw,
        "voltage": round(voltage, 3),
    }
