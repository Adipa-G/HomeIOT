# Fan Control

This project uses a Raspberry Pi Pico W to control an **ARCTIC P12 PWM fan**
based on temperature readings from a **DS18B20** sensor.

## How it works

- The Pico W reads the temperature from the DS18B20 sensor.
- It sets the fan's PWM signal to 25 kHz and selects a speed based on the
  measured temperature:
  - Below 35 degrees C: off
  - 35 to below 40 degrees C: 25%
  - 40 to below 45 degrees C: 50%
  - 45 degrees C and above: 100%
- It reads the fan's tachometer signal for one second to estimate the fan
  speed in RPM. If the fan does not start at a target speed below 30%, it briefly
  runs the fan at 50% and then retries the target speed.

The controller is implemented in `main.py`. The temperature sensor data pin is
GPIO 26, the fan PWM pin is GPIO 3, and the fan tachometer pin is GPIO 2.

## PCB design and power

The PCB is designed in KiCad, with the project files located in
[`kicad-pcb-design`](kicad-pcb-design). It takes a 12 V input and uses a buck
converter module to step it down to 5 V for the Raspberry Pi Pico W.
