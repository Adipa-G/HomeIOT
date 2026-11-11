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
  probe doesn't corrode. It waits 100 ms for the sensor to settle, reads it,
  then switches the power off again, even if the read fails.
- Reads the rain sensor's analog output on GPIO 27 as a wetness value from
  0 (dry) to 1023 (soaked). It also reads the digital output on GPIO 1, which
  is low while wet. The digital reading is only reported.
- Keeps the peak wetness over a sliding 12-hour window in memory. A reboot
  clears it.
- Opens the valve on GPIO 0 from `VALVE_START_TIME` (local time) for
  `VALVE_RUN_DURATION_MINUTES`. The decision is made once, at the start of the
  window:
  - If the 12-hour peak is above `RAIN_THRESHOLD_LAST_12H`, the window is
    skipped.
  - Otherwise the valve stays open for the whole window, even if it starts
    raining.
- Keeps the valve closed until the clock is synced, and closes it if the run
  fails.
- Opens the valve on the next run when `TURN_VALVE_ON_MANUALLY` is set to
  `true`. This ignores the schedule, rain and clock sync. The valve stays open
  until the variable is set back to `false`, then the schedule takes over
  again. Rain is still tracked while it's on.

### Indicator LEDs

| Pin    | On when |
|--------|---------|
| GPIO 2 | The 12-hour peak wetness is above `RAIN_THRESHOLD_LAST_12H` right now. |
| GPIO 3 | The valve won't run today. Either the current window was skipped, or the rain won't age out of the 12-hour window before the next start. |

Both LEDs clear on their own. GPIO 2 clears once 12 hours pass with no
reading above the threshold. GPIO 3 clears once the skipped window has passed
and the next window is far enough away for the rain to age out by then.

### Module variables

These can be overridden with module variables. If a variable isn't set, the
default is used.

| Variable                     | Default   | Description |
|------------------------------|-----------|-------------|
| `VALVE_START_TIME`           | `"17:00"` | Local start time (`HH:MM`). |
| `VALVE_RUN_DURATION_MINUTES` | `10`      | How long the valve stays open. |
| `RAIN_THRESHOLD_LAST_12H`    | `100`     | Peak wetness (0-1023) in the last 12 hours that skips watering. |
| `UTC_OFFSET_MINUTES`         | `600`     | Standard-time offset from UTC. |
| `USE_AU_DST`                 | `true`    | Apply Australian daylight saving (first Sunday in October to first Sunday in April). |
| `TURN_VALVE_ON_MANUALLY`     | `false`   | Hold the valve open regardless of schedule and rain. Use a boolean variable with a toggle control. |

## PCB design and power

The PCB is designed in KiCad, with the project files located in
[`kicad-pcb-design`](kicad-pcb-design). It takes a solar panel input and charge a 18650 battery and use this to run the timer. 
