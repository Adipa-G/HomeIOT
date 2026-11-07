import sys
import time

# --- PIN CONFIGURATION ---
TEMP_SENSOR_PIN = 26
PWM_FAN_PIN = 3
TACH_FAN_PIN = 2


def run(ctx):
    platform = sys.platform
    if platform != "rp2":
        return {
            "success": False,
            "platform": platform,
            "error": "Module not supported on platform: {}".format(platform),
        }

    try:
        import machine
        import onewire
        import ds18x20

        ds_pin = machine.Pin(TEMP_SENSOR_PIN)
        ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
        roms = ds_sensor.scan()
        if not roms:
            return {
                "success": False,
                "platform": platform,
                "error": "No DS18X20 sensors found.",
            }

        fan_pwm = machine.PWM(machine.Pin(PWM_FAN_PIN))
        fan_pwm.freq(25000)
        tach_pin = machine.Pin(
            TACH_FAN_PIN, machine.Pin.IN, machine.Pin.PULL_UP
        )
        pulse_count = [0]

        def tach_callback(pin):
            pulse_count[0] += 1

        tach_pin.irq(
            trigger=machine.Pin.IRQ_FALLING,
            handler=tach_callback,
        )

        def set_fan_speed(target_percent):
            target_percent = max(0, min(100, target_percent))
            duty = int((target_percent / 100) * 65535)
            fan_pwm.duty_u16(duty)

        def read_fan_rpm():
            pulse_count[0] = 0
            time.sleep(1.0)
            return (pulse_count[0] / 2) * 60

        ds_sensor.convert_temp()
        temp = ds_sensor.read_temp(roms[0])

        if temp < 35.0:
            target_speed = 0
        elif temp < 40.0:
            target_speed = 25
        elif temp < 45.0:
            target_speed = 50
        else:
            target_speed = 100

        set_fan_speed(target_speed)
        rpm = read_fan_rpm()
        if 0 < target_speed < 30 and rpm == 0:
            fan_pwm.duty_u16(int((50 / 100) * 65535))
            time.sleep(0.4)
            set_fan_speed(target_speed)
            rpm = read_fan_rpm()

        return {
            "success": True,
            "platform": platform,
            "temperature": temp,
            "target_speed": target_speed,
            "rpm": int(rpm),
        }
    except Exception as e:
        return {
            "success": False,
            "platform": platform,
            "error": str(e),
        }