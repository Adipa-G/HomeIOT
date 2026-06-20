from edge.shared.app.dev_command_runtime import execute_dev_command


NETWORK_RETRY_BASE_MS = 5000
NETWORK_RETRY_MAX_MS = 60000

PRODUCTION_SLEEP_MIN_MS = 500
PRODUCTION_SLEEP_MAX_MS = 5000
DEVELOPMENT_SLEEP_MIN_MS = 50
DEVELOPMENT_SLEEP_MAX_MS = 1000


def run_control_loop(
    system,
    presence,
    device_control,
    module_runtime,
    logger,
    config,
    network=None,
    watchdog=None,
    updater=None,
    max_iterations=None,
):
    mode = "production"
    heartbeat_interval_ms = config.heartbeat_interval_ms
    dev_poll_interval_ms = config.dev_poll_interval_ms
    module_poll_interval_ms = config.module_assignment_poll_interval_ms
    ota_poll_interval_ms = config.ota_poll_interval_ms
    power_cfg = getattr(config, "power", None)
    production_sleep_min_ms = getattr(power_cfg, "production_sleep_min_ms", PRODUCTION_SLEEP_MIN_MS)
    production_sleep_max_ms = getattr(power_cfg, "production_sleep_max_ms", PRODUCTION_SLEEP_MAX_MS)
    development_sleep_min_ms = getattr(power_cfg, "development_sleep_min_ms", DEVELOPMENT_SLEEP_MIN_MS)
    development_sleep_max_ms = getattr(power_cfg, "development_sleep_max_ms", DEVELOPMENT_SLEEP_MAX_MS)
    network_retry_base_ms = getattr(power_cfg, "network_retry_base_ms", NETWORK_RETRY_BASE_MS)
    network_retry_max_ms = getattr(power_cfg, "network_retry_max_ms", NETWORK_RETRY_MAX_MS)

    network_retry_interval_ms = network_retry_base_ms
    last_applied_power_mode = None

    next_heartbeat_ms = 0
    next_dev_poll_ms = 0
    next_module_poll_ms = 0
    next_ota_poll_ms = 0
    next_network_retry_ms = 0

    last_dev_revision_hash = None
    last_assignment_hash = None
    iterations = 0

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            return

        now = system.time_ms()

        if watchdog is not None:
            _safe_watchdog_feed(watchdog, logger)

        network_ready = _ensure_network_connected(
            network=network,
            config=config,
            logger=logger,
            now_ms=now,
            next_retry_ms=next_network_retry_ms,
            retry_interval_ms=network_retry_interval_ms,
            retry_base_ms=network_retry_base_ms,
            retry_max_ms=network_retry_max_ms,
        )
        if network is not None and not network_ready["connected"]:
            next_network_retry_ms = network_ready["next_retry_ms"]
            network_retry_interval_ms = network_ready["retry_interval_ms"]
        elif network is not None and network_ready["connected"]:
            network_retry_interval_ms = network_retry_base_ms

        if network is None or network_ready["connected"]:
            if hasattr(module_runtime, "flush_pending_timeout_result"):
                try:
                    module_runtime.flush_pending_timeout_result()
                except Exception as exc:
                    logger.warn("Pending timeout result flush failed", {"error": str(exc)})

            if hasattr(module_runtime, "flush_pending_module_status"):
                try:
                    module_runtime.flush_pending_module_status()
                except Exception as exc:
                    logger.warn("Pending module-status flush failed", {"error": str(exc)})


            if now >= next_heartbeat_ms:
                try:
                    metadata = presence.heartbeat_with_metadata()
                except Exception as exc:
                    logger.warn("Heartbeat poll threw exception", {"error": str(exc)})
                    metadata = None

                if isinstance(metadata, dict) and metadata:
                    server_mode = str(metadata.get("mode", mode))
                    if server_mode != mode:
                        logger.info("Mode changed", {"from": mode, "to": server_mode})
                    mode = server_mode
                    heartbeat_interval_ms = max(1000, int(metadata.get("next_heartbeat_ms", heartbeat_interval_ms)))
                    dev_poll_interval_ms = max(500, int(metadata.get("dev_poll_interval_ms", dev_poll_interval_ms)))
                    module_poll_interval_ms = max(
                        1000,
                        int(metadata.get("module_assignment_poll_interval_ms", module_poll_interval_ms)),
                    )

                logger.info(
                    "Heartbeat sent",
                    {
                        "mode": mode,
                        "interval_ms": heartbeat_interval_ms,
                    },
                )

                next_heartbeat_ms = now + heartbeat_interval_ms
 
                if network is None or network_ready["connected"]:
                    upcoming = module_runtime.get_upcoming_modules(next_wake_ms=next_heartbeat_ms)
                    if upcoming:
                        try:
                            logger.info(
                                "Module prefetch attempt",
                                {
                                    "source": "imminent_next_loop",
                                    "upcoming_count": len(upcoming),
                                    "next_heartbeat_ms": next_heartbeat_ms,
                                    "mode": mode,
                                },
                            )
                            ok = device_control.prefetch_server_code(upcoming)
                            if not ok:
                                logger.warn("Module prefetch rejected", {"upcoming_count": len(upcoming)})
                        except Exception as exc:
                            logger.warn("Module prefetch failed", {"error": str(exc)})

            if now >= next_module_poll_ms:
                try:
                    assignment = device_control.get_module_assignment(last_assignment_hash)
                except Exception as exc:
                    logger.warn("Module assignment poll threw exception", {"error": str(exc)})
                    assignment = None
                if assignment:
                    last_assignment_hash = assignment.get("assignment_hash", last_assignment_hash)
                    reconcile = device_control.ensure_assigned_modules_present(assignment)
                    module_runtime.update_assignment(assignment, now_ms=now)
                    logger.info("Module assignment reconciled", reconcile)
                next_module_poll_ms = now + module_poll_interval_ms

            if updater is not None and now >= next_ota_poll_ms:
                try:
                    update_info = updater.check()
                except Exception as exc:
                    logger.warn("OTA check threw exception", {"error": str(exc)})
                    update_info = None
                if update_info is not None:
                    logger.info("OTA update available", {"version": update_info.version})
                    try:
                        updater.apply(update_info)
                    except Exception as exc:
                        logger.warn("OTA apply threw exception", {"error": str(exc)})
                next_ota_poll_ms = now + ota_poll_interval_ms

            if mode == "development" and now >= next_dev_poll_ms:
                try:
                    command = device_control.get_next_dev_command(last_dev_revision_hash)
                except Exception as exc:
                    logger.warn("Dev command poll threw exception", {"error": str(exc)})
                    command = None
                if command and device_control.should_execute_dev_command(command, last_dev_revision_hash):
                    last_dev_revision_hash = command.get("revision_hash", last_dev_revision_hash)
                    result = execute_dev_command(
                        system=system,
                        device_control=device_control,
                        command=command,
                        logger=logger,
                    )
                    logger.info(
                        "Dev command executed",
                        {
                            "command_id": command.get("command_id"),
                            "revision_hash": last_dev_revision_hash,
                            "status": result.get("status"),
                            "reported": result.get("reported"),
                        },
                    )
                next_dev_poll_ms = now + dev_poll_interval_ms

        if network is not None and network_ready["connected"]:
            requested_power_mode = _requested_network_power_mode(config, mode)
            if requested_power_mode != last_applied_power_mode:
                if _try_apply_network_power_mode(network, requested_power_mode, logger):
                    last_applied_power_mode = requested_power_mode

        runtime_tick = module_runtime.tick(now_ms=now)
        if runtime_tick.get("reset_requested"):
            return

        logger.tick()

        sleep_candidates = [next_heartbeat_ms, next_module_poll_ms]
        if network is not None and not network_ready["connected"]:
            sleep_candidates.append(next_network_retry_ms)
        if mode == "development":
            sleep_candidates.append(next_dev_poll_ms)

        sleep_until = min(sleep_candidates)

        if mode == "development":
            sleep_ms = max(development_sleep_min_ms, min(development_sleep_max_ms, sleep_until - now))
        else:
            sleep_ms = max(production_sleep_min_ms, min(production_sleep_max_ms, sleep_until - now))

        system.sleep_ms(sleep_ms)
        iterations += 1


def _requested_network_power_mode(config, mode):
    power_cfg = getattr(config, "power", None)
    if power_cfg is None or not getattr(power_cfg, "wifi_power_save_enabled", False):
        return "none"
    if mode == "development":
        return str(getattr(power_cfg, "wifi_power_save_development_mode", "none") or "none").lower()
    return str(getattr(power_cfg, "wifi_power_save_production_mode", "modem") or "modem").lower()


def _try_apply_network_power_mode(network, mode, logger):
    if not hasattr(network, "set_power_save"):
        return False
    try:
        network.set_power_save(mode)
        logger.info("WiFi power mode applied", {"mode": mode})
        return True
    except Exception as exc:
        logger.warn("WiFi power mode apply failed", {"mode": mode, "error": str(exc)})
        return False


def _ensure_network_connected(
    network,
    config,
    logger,
    now_ms,
    next_retry_ms,
    retry_interval_ms,
    retry_base_ms,
    retry_max_ms,
):
    if network is None:
        return {
            "connected": True,
            "next_retry_ms": next_retry_ms,
            "retry_interval_ms": retry_base_ms,
        }

    try:
        connected = network.is_connected()
    except Exception as exc:
        logger.warn("Network state check failed", {"error": str(exc)})
        connected = False

    if connected:
        return {
            "connected": True,
            "next_retry_ms": now_ms,
            "retry_interval_ms": retry_base_ms,
        }

    if now_ms < next_retry_ms:
        return {
            "connected": False,
            "next_retry_ms": next_retry_ms,
            "retry_interval_ms": retry_interval_ms,
        }

    try:
        network.connect(config.wifi_ssid, config.wifi_password)
        logger.info("WiFi connected", {"ip": network.get_ip()})
        return {
            "connected": True,
            "next_retry_ms": now_ms,
            "retry_interval_ms": retry_base_ms,
        }
    except Exception as exc:
        logger.warn("WiFi reconnect failed", {"error": str(exc)})
        next_interval = min(retry_max_ms, max(retry_base_ms, retry_interval_ms * 2))
        return {
            "connected": False,
            "next_retry_ms": now_ms + retry_interval_ms,
            "retry_interval_ms": next_interval,
        }


def _safe_watchdog_feed(watchdog, logger):
    try:
        watchdog.feed()
    except Exception as exc:
        logger.warn("Watchdog feed failed", {"error": str(exc)})
