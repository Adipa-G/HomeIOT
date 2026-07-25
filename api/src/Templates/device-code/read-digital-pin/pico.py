from machine import Pin

# Change this to the GPIO pin number your button/switch/sensor is wired to.
PIN_NUMBER = 15

_pin = Pin(PIN_NUMBER, Pin.IN, Pin.PULL_UP)


def run(ctx):
    value = _pin.value()
    return {
        "pin": PIN_NUMBER,
        "value": value,
        "is_high": value == 1,
    }
