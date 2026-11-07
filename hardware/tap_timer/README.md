# Fan Control

This project uses a Raspberry Pi Pico W to control a 12V water valve.
The board is designed to be able to be able to connect to multiple other sensors and also indicate different statuses using LEDs.

## PCB design and power

The PCB is designed in KiCad, with the project files located in
[`kicad-pcb-design`](kicad-pcb-design). It takes a solar panel input and charge a 18650 battery and use this to run the timer. 
