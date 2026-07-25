import esp32


def run(ctx):
    raw_temp = esp32.raw_temperature()  # degrees Fahrenheit
    temp_celsius = (raw_temp - 32) * 5 / 9
    return {
        "raw_value": raw_temp,
        "temp_celsius": round(temp_celsius, 1),
    }
