# Tap Timer

This project uses a Raspberry Pi Pico W to control a 12V water valve.
The board is designed to be able to be able to connect to multiple other sensors and also indicate different statuses using LEDs.

## How it works

`main.py` is a HomeIOT device module. Assign it with a short interval (for
example `interval_ms` = 60000). Each run checks whether the valve should be
open right now, so the valve closes within one interval of the window ending.
Keep the interval shorter than `VALVE_RUN_DURATION_MINUTES`, or a whole window
can be missed.

On each run the module:

- Reads the battery voltage from GPIO 26. This pin gets half of VSYS through a
  divider, so the voltage is doubled.
- Powers the rain sensor from GPIO 4 only while taking a reading, so the
  probe doesn't corrode.
- Reads the rain sensor's analog output on GPIO 27 as a wetness value from
  0 (dry) to 1023 (soaked). It also reads the digital output on GPIO 1, which
  is low while wet. The digital reading is only reported.
- Opens the valve on GPIO 0 from `VALVE_START_TIME` for
  `VALVE_RUN_DURATION_MINUTES`, as long as the current wetness is at or below
  `RAIN_THRESHOLD`. Once open, it stays open for the whole window even if it
  starts raining. There's no rain history: if the sensor dries out partway
  through a skipped window, the valve opens for the rest of it.
- Uses a fixed UTC+10 (AEST) clock with no daylight saving, so a 17:00 start
  happens at 18:00 by the clock in summer.
- Keeps the valve closed until the clock is synced, and closes it if the run
  fails.
- Opens the valve when `TURN_VALVE_ON_MANUALLY` is set to `true`, ignoring the
  schedule, rain and clock sync. It stays open until the variable is set back
  to `false`.

The module stores nothing between runs. It reads the valve and indicator pins
back to remember what it decided last time. A reboot sets them all low.

The source is kept small on purpose. The Pico W ran out of memory compiling an
11 KB version of this module.

### Indicator LEDs

| Pin    | On when |
|--------|---------|
| GPIO 2 | The current wetness is above `RAIN_THRESHOLD`. |
| GPIO 3 | Rain skipped today's window. It stays on until midnight. |

### Module variables

These can be overridden with module variables. If a variable isn't set, the
default is used.

| Variable                     | Default   | Description |
|------------------------------|-----------|-------------|
| `VALVE_START_TIME`           | `"17:00"` | Start time (`HH:MM`, AEST). |
| `VALVE_RUN_DURATION_MINUTES` | `10`      | How long the valve stays open. |
| `RAIN_THRESHOLD`             | `100`     | Wetness (0-1023) above which the window is skipped. |
| `TURN_VALVE_ON_MANUALLY`     | `false`   | Hold the valve open regardless of schedule and rain. Use a boolean variable with a toggle control. |

## PCB design and power

The PCB is designed in KiCad, with the project files located in
[`kicad-pcb-design`](kicad-pcb-design). It takes a solar panel input and charge a 18650 battery and use this to run the timer. 
