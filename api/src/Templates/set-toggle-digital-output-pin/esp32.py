from machine import Pin

# Change this to the GPIO pin your LED/relay is wired to.
PIN_NUMBER = 2

_pin = Pin(PIN_NUMBER, Pin.OUT)


def run(ctx):
    # PIN_STATE is an input variable you configure on the module (Type: boolean).
    # Falls back to False until it's configured.
    state = False
    try:
        state = bool(PIN_STATE)
    except NameError:
        pass

    _pin.value(1 if state else 0)

    return {
        "pin": PIN_NUMBER,
        "state": state,
    }
