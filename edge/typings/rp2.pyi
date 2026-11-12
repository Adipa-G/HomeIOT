# Type stubs for the Pico W (rp2 port) parts of the MicroPython API that the
# edge code uses. The ESP32 stub package (micropython-esp32-stubs) covers
# everything else; add declarations here as Pico-only APIs come into use.
# Reference: https://docs.micropython.org/en/v1.28.0/library/rp2.html

def country(country: str | None = None, /) -> str:
    """Get or set the two-letter ISO 3166-1 country code for the WiFi radio."""
