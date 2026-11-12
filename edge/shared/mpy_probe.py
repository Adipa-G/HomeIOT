# Shipped at the release root as mpy_probe.mpy, compiled with the rest of the release.
# The updater and the first-boot installer import it before installing: if the
# firmware can't load it, it can't load the release's other .mpy files either.
OK = 1
