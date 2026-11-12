# HomeIOT first-boot installer.
#
# Copy this file to a freshly flashed MicroPython device as main.py and reset it.
# It unpacks the embedded firmware modules, writes config.json from the embedded
# provisioning data and installs the latest firmware release through the regular
# OTA updater. The firmware replaces this file once the install succeeds.
#
# Contains plaintext credentials - do not share or commit the generated file.
import sys

TYPE_CHECKING = False
if TYPE_CHECKING:  # never true on a device
    from collections.abc import Callable
    from types import ModuleType

    from edge.shared.hal.interfaces import IFileSystem, IHttpClient, INetwork, ISystem

LIB_DIR = "bootstrap_lib"
SELF_PATH = "main.py"
TEMPLATE_NAME = "config.json"
PROBE_MODULE = "mpy_probe"
RETRY_DELAY_MS = 60000

PROVISION_MARKER = "#@@PROVISION "
FILE_MARKER = "#@@FILE "
BINARY_FILE_MARKER = "#@@BFILE "
LINE_MARKER = "#|"
END_MARKER = "#@@END"


def _is_dir(os_mod: "ModuleType", path: str) -> bool:
    try:
        return (os_mod.stat(path)[0] & 0x4000) == 0x4000
    except OSError:
        return False


def _exists(os_mod: "ModuleType", path: str) -> bool:
    try:
        os_mod.stat(path)
        return True
    except OSError:
        return False


def _makedirs(os_mod: "ModuleType", path: str) -> None:
    current = ""
    for part in path.split("/"):
        if not part:
            continue
        current = current + "/" + part if current else part
        if not _exists(os_mod, current):
            os_mod.mkdir(current)


def remove_tree(os_mod: "ModuleType", path: str) -> None:
    if not _exists(os_mod, path):
        return
    if _is_dir(os_mod, path):
        for name in os_mod.listdir(path):
            remove_tree(os_mod, path + "/" + name)
        os_mod.rmdir(path)
    else:
        os_mod.remove(path)


def import_probe(lib_dir: str) -> None:
    """Import the release's mpy_probe so the firmware's own loader checks the .mpy format."""
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    try:
        __import__(PROBE_MODULE)
    except Exception as exc:
        raise ValueError(
            "This firmware can't load the installer's compiled modules (" + str(exc)
            + "); flash a MicroPython release this installer supports"
        )
    finally:
        sys.modules.pop(PROBE_MODULE, None)


def extract_payload(os_mod: "ModuleType", source_path: str = SELF_PATH, lib_dir: str = LIB_DIR) -> str | None:
    """Unpack the comment-encoded payload of source_path into lib_dir.

    Returns the raw provisioning JSON string (or None when absent). Reading
    line by line keeps memory flat regardless of payload size. Binary (.mpy)
    blocks are base64, one independently decodable chunk per line.
    """
    from binascii import a2b_base64

    remove_tree(os_mod, lib_dir)
    _makedirs(os_mod, lib_dir)
    provision = None
    out = None
    binary = False
    with open(source_path, "r") as source:
        for line in source:
            if out is not None:
                if line.startswith(LINE_MARKER):
                    data = line[len(LINE_MARKER):].rstrip("\r\n")
                    if binary:
                        out.write(a2b_base64(data))
                    else:
                        out.write(data)
                        out.write("\n")
                    continue
                if line.startswith(END_MARKER):
                    out.close()
                    out = None
                    continue
                out.close()
                raise ValueError("Corrupt payload: unterminated file block")
            if line.startswith(PROVISION_MARKER):
                provision = line[len(PROVISION_MARKER):].rstrip("\r\n")
            elif line.startswith(FILE_MARKER) or line.startswith(BINARY_FILE_MARKER):
                binary = line.startswith(BINARY_FILE_MARKER)
                rel_path = line[len(BINARY_FILE_MARKER if binary else FILE_MARKER):].strip()
                if rel_path.startswith("/") or ".." in rel_path:
                    raise ValueError("Unsafe payload path: " + rel_path)
                target = lib_dir + "/" + rel_path
                if "/" in rel_path:
                    _makedirs(os_mod, target.rsplit("/", 1)[0])
                out = open(target, "wb" if binary else "w")
    if out is not None:
        out.close()
        raise ValueError("Corrupt payload: missing end marker")
    return provision


def run(
    os_mod: "ModuleType | None" = None,
    services: "tuple[IFileSystem, ISystem, INetwork, IHttpClient] | None" = None,
    source_path: str = SELF_PATH,
    lib_dir: str = LIB_DIR,
    probe: "Callable[[str], None] | None" = None,
) -> None:
    import json

    if os_mod is None:
        import os as os_mod
    if probe is None and sys.implementation.name == "micropython":
        # CPython (tests) can't load .mpy, so it skips the probe.
        probe = import_probe

    print("[bootstrap] Unpacking installer payload")
    provision_json = extract_payload(os_mod, source_path, lib_dir)
    if not provision_json:
        raise ValueError("Provisioning data missing from main.py")
    provision = json.loads(provision_json)

    with open(lib_dir + "/" + TEMPLATE_NAME, "r") as handle:
        template = json.loads(handle.read())

    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    if probe is not None and _exists(os_mod, lib_dir + "/" + PROBE_MODULE + ".mpy"):
        probe(lib_dir)
    from edge.bootstrap.bootstrap import create_device_services, run_bootstrap

    if services is None:
        services = create_device_services()

    # Every module needed from here on is imported; free the flash space.
    remove_tree(os_mod, lib_dir)

    fs, system, network, http = services
    run_bootstrap(fs, system, network, http, provision, template)


def main() -> None:
    try:
        run()
    except Exception as exc:
        print("[bootstrap] Install failed:", exc)
        if hasattr(sys, "print_exception"):
            getattr(sys, "print_exception")(exc)  # MicroPython-only
        print("[bootstrap] Retrying in", RETRY_DELAY_MS // 1000, "seconds (Ctrl-C to stop)")
        import time

        if hasattr(time, "sleep_ms"):
            getattr(time, "sleep_ms")(RETRY_DELAY_MS)  # MicroPython-only
        else:
            time.sleep(RETRY_DELAY_MS / 1000)
        import machine

        machine.reset()


if __name__ == "__main__":
    main()
