# HomeIOT first-boot installer.
#
# Copy this file to a freshly flashed MicroPython device as main.py and reset it.
# It unpacks the embedded firmware modules, writes config.json from the embedded
# provisioning data and installs the latest firmware release through the regular
# OTA updater. The firmware replaces this file once the install succeeds.
#
# Contains plaintext credentials - do not share or commit the generated file.
import sys

LIB_DIR = "bootstrap_lib"
SELF_PATH = "main.py"
TEMPLATE_NAME = "config.json"
RETRY_DELAY_MS = 60000

PROVISION_MARKER = "#@@PROVISION "
FILE_MARKER = "#@@FILE "
LINE_MARKER = "#|"
END_MARKER = "#@@END"


def _is_dir(os_mod, path):
    try:
        return (os_mod.stat(path)[0] & 0x4000) == 0x4000
    except OSError:
        return False


def _exists(os_mod, path):
    try:
        os_mod.stat(path)
        return True
    except OSError:
        return False


def _makedirs(os_mod, path):
    current = ""
    for part in path.split("/"):
        if not part:
            continue
        current = current + "/" + part if current else part
        if not _exists(os_mod, current):
            os_mod.mkdir(current)


def remove_tree(os_mod, path):
    if not _exists(os_mod, path):
        return
    if _is_dir(os_mod, path):
        for name in os_mod.listdir(path):
            remove_tree(os_mod, path + "/" + name)
        os_mod.rmdir(path)
    else:
        os_mod.remove(path)


def extract_payload(os_mod, source_path=SELF_PATH, lib_dir=LIB_DIR):
    """Unpack the comment-encoded payload of source_path into lib_dir.

    Returns the raw provisioning JSON string (or None when absent). Reading
    line by line keeps memory flat regardless of payload size.
    """
    remove_tree(os_mod, lib_dir)
    _makedirs(os_mod, lib_dir)
    provision = None
    out = None
    with open(source_path, "r") as source:
        for line in source:
            if out is not None:
                if line.startswith(LINE_MARKER):
                    out.write(line[len(LINE_MARKER):].rstrip("\r\n"))
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
            elif line.startswith(FILE_MARKER):
                rel_path = line[len(FILE_MARKER):].strip()
                if rel_path.startswith("/") or ".." in rel_path:
                    raise ValueError("Unsafe payload path: " + rel_path)
                target = lib_dir + "/" + rel_path
                if "/" in rel_path:
                    _makedirs(os_mod, target.rsplit("/", 1)[0])
                out = open(target, "w")
    if out is not None:
        out.close()
        raise ValueError("Corrupt payload: missing end marker")
    return provision


def run(os_mod=None, services=None, source_path=SELF_PATH, lib_dir=LIB_DIR):
    import json

    if os_mod is None:
        import os as os_mod

    print("[bootstrap] Unpacking installer payload")
    provision_json = extract_payload(os_mod, source_path, lib_dir)
    if not provision_json:
        raise ValueError("Provisioning data missing from main.py")
    provision = json.loads(provision_json)

    with open(lib_dir + "/" + TEMPLATE_NAME, "r") as handle:
        template = json.loads(handle.read())

    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    from edge.bootstrap.bootstrap import create_device_services, run_bootstrap

    if services is None:
        services = create_device_services()

    # Every module needed from here on is imported; free the flash space.
    remove_tree(os_mod, lib_dir)

    fs, system, network, http = services
    run_bootstrap(fs, system, network, http, provision, template)


def main():
    try:
        run()
    except Exception as exc:
        print("[bootstrap] Install failed:", exc)
        if hasattr(sys, "print_exception"):
            sys.print_exception(exc)
        print("[bootstrap] Retrying in", RETRY_DELAY_MS // 1000, "seconds (Ctrl-C to stop)")
        import time

        if hasattr(time, "sleep_ms"):
            time.sleep_ms(RETRY_DELAY_MS)
        else:
            time.sleep(RETRY_DELAY_MS / 1000)
        import machine

        machine.reset()


if __name__ == "__main__":
    main()
