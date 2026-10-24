from edge.shared.app.dev_command_runtime import execute_dev_command


NETWORK_RETRY_BASE_MS = 5000
NETWORK_RETRY_MAX_MS = 60000

PRODUCTION_SLEEP_MIN_MS = 500
PRODUCTION_SLEEP_MAX_MS = 5000
DEVELOPMENT_SLEEP_MIN_MS = 50
DEVELOPMENT_SLEEP_MAX_MS = 1000
RADIO_OFF_SLEEP_MIN_MS = 15000

# A light sleep that returns faster than this is treated as not having slept
# (e.g. rp2 returns immediately while the CYW43 chip has pending work).
LIGHT_SLEEP_INEFFECTIVE_MS = 10
LIGHT_SLEEP_MAX_INEFFECTIVE = 3

TIME_SYNC_INTERVAL_MS = 24 * 60 * 60 * 1000
TIME_SYNC_RETRY_MS = 5 * 60 * 1000


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
    radio_off_sleep_min_ms = getattr(power_cfg, "radio_off_sleep_min_ms", RADIO_OFF_SLEEP_MIN_MS)

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

    sleep_capabilities = None
    if hasattr(system, "get_sleep_capabilities"):
        try:
            sleep_capabilities = system.get_sleep_capabilities()
            logger.info("CPU sleep capabilities", sleep_capabilities)
        except Exception as exc:
            logger.warn("CPU sleep capability detection failed", {"error": str(exc)})

    if network is not None and hasattr(network, "get_power_save_modes"):
        try:
            logger.info("WiFi power-save modes", {"modes": sorted(network.get_power_save_modes())})
        except Exception as exc:
            logger.warn("WiFi power-save capability detection failed", {"error": str(exc)})

    radio_off_sleep_enabled = _radio_off_sleep_available(
        power_cfg, system, network, sleep_capabilities, radio_off_sleep_min_ms, logger
    )
    sleep_chunk_ms = _watchdog_feed_interval_ms(watchdog, logger)
    light_sleep_failures = 0
    next_time_sync_ms = None

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
            system=system,
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
            if network is not None:
                next_time_sync_ms = _maybe_sync_time(system, logger, now, next_time_sync_ms, module_runtime)

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

            if hasattr(module_runtime, "flush_pending_results"):
                try:
                    module_runtime.flush_pending_results()
                except Exception as exc:
                    logger.warn("Pending module result flush failed", {"error": str(exc)})

            if system.ticks_diff(now, next_heartbeat_ms) >= 0:
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

                next_heartbeat_ms = system.ticks_add(now, heartbeat_interval_ms)
 
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

                _feed_watchdog(watchdog, logger)

            if system.ticks_diff(now, next_module_poll_ms) >= 0:
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
                next_module_poll_ms = system.ticks_add(now, module_poll_interval_ms)
                _feed_watchdog(watchdog, logger)

            if updater is not None and system.ticks_diff(now, next_ota_poll_ms) >= 0:
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
                next_ota_poll_ms = system.ticks_add(now, ota_poll_interval_ms)
                _feed_watchdog(watchdog, logger)

            if mode == "development" and system.ticks_diff(now, next_dev_poll_ms) >= 0:
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
                next_dev_poll_ms = system.ticks_add(now, dev_poll_interval_ms)
                _feed_watchdog(watchdog, logger)

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
        next_module_due_ms = _next_module_due_ms(module_runtime, logger)
        if next_module_due_ms is not None:
            sleep_candidates.append(next_module_due_ms)

        sleep_until = min(sleep_candidates, key=lambda candidate: system.ticks_diff(candidate, now))
        sleep_remaining_ms = system.ticks_diff(sleep_until, now)

        if mode == "development":
            sleep_ms = max(development_sleep_min_ms, min(development_sleep_max_ms, sleep_remaining_ms))
        else:
            sleep_ms = max(production_sleep_min_ms, min(production_sleep_max_ms, sleep_remaining_ms))

        _feed_watchdog(watchdog, logger)

        if radio_off_sleep_enabled and mode != "development" and sleep_ms >= radio_off_sleep_min_ms:
            was_connected = network_ready["connected"]
            if was_connected:
                # Buffered logs can't be sent while the radio is off, and are lost
                # if the device resets before the next wake.
                _flush_logs(logger, "pre_sleep")
            if _suspend_network(network, logger):
                sleep_stats = _light_sleep(system, watchdog, logger, sleep_ms, sleep_chunk_ms)
                logger.info(
                    "Radio-off sleep finished",
                    {
                        "sleep_ms": sleep_ms,
                        "light_slept_ms": sleep_stats["light_slept_ms"],
                        "light_sleep_steps": sleep_stats["effective_steps"],
                        "steps": sleep_stats["steps"],
                    },
                )
                if sleep_stats["effective_steps"] > 0:
                    light_sleep_failures = 0
                else:
                    light_sleep_failures += 1
                    if light_sleep_failures >= LIGHT_SLEEP_MAX_INEFFECTIVE:
                        radio_off_sleep_enabled = False
                        logger.warn(
                            "Light sleep is not sleeping; radio-off sleep disabled",
                            {"failed_cycles": light_sleep_failures},
                        )
                # Radio power-down resets the driver's power-save mode.
                last_applied_power_mode = None
                if was_connected:
                    next_network_retry_ms = system.time_ms()
                    network_retry_interval_ms = network_retry_base_ms
            else:
                radio_off_sleep_enabled = False
                _sleep(system, watchdog, logger, sleep_ms, sleep_chunk_ms)
        else:
            _sleep(system, watchdog, logger, sleep_ms, sleep_chunk_ms)
        iterations += 1


def _requested_network_power_mode(config, mode):
    power_cfg = getattr(config, "power", None)
    if power_cfg is None or not getattr(power_cfg, "wifi_power_save_enabled", False):
        return "none"
    if mode == "development":
        requested_mode = str(getattr(power_cfg, "wifi_power_save_development_mode", "none") or "none").lower()
    else:
        requested_mode = str(getattr(power_cfg, "wifi_power_save_production_mode", "modem") or "modem").lower()
    return "powersave" if requested_mode == "light" else requested_mode


def _try_apply_network_power_mode(network, mode, logger):
    if not hasattr(network, "set_power_save"):
        return False
    try:
        accepted = network.set_power_save(mode)
        if accepted is not True:
            logger.warn("WiFi power mode unsupported or rejected", {"mode": mode})
            return False
        logger.info("WiFi power mode accepted", {"mode": mode})
        return True
    except Exception as exc:
        logger.warn("WiFi power mode apply failed", {"mode": mode, "error": str(exc)})
        return False


def _ensure_network_connected(
    network,
    config,
    logger,
    system,
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

    if system.ticks_diff(now_ms, next_retry_ms) < 0:
        return {
            "connected": False,
            "next_retry_ms": next_retry_ms,
            "retry_interval_ms": retry_interval_ms,
        }

    try:
        started_ms = system.time_ms()
        network.connect(config.wifi_ssid, config.wifi_password)
        logger.info(
            "WiFi connected",
            {"ip": network.get_ip(), "connect_ms": system.ticks_diff(system.time_ms(), started_ms)},
        )
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
            "next_retry_ms": system.ticks_add(now_ms, retry_interval_ms),
            "retry_interval_ms": next_interval,
        }


def _safe_watchdog_feed(watchdog, logger):
    try:
        watchdog.feed()
    except Exception as exc:
        logger.warn("Watchdog feed failed", {"error": str(exc)})


def _feed_watchdog(watchdog, logger):
    if watchdog is not None:
        _safe_watchdog_feed(watchdog, logger)


def _flush_logs(logger, reason):
    if not hasattr(logger, "flush"):
        return
    try:
        logger.flush(reason)
    except Exception:
        pass


def _maybe_sync_time(system, logger, now_ms, next_sync_ms, module_runtime=None):
    """Sync the wall clock over NTP while connected; returns the next sync deadline.

    Syncs immediately if the clock was never set (e.g. the device booted while
    offline, so module results would carry a 2021 date), then once a day.
    """
    if not hasattr(system, "sync_time"):
        return next_sync_ms
    if next_sync_ms is not None and system.ticks_diff(now_ms, next_sync_ms) < 0:
        return next_sync_ms

    clock_set = _clock_is_set(system)
    if next_sync_ms is None and clock_set:
        # Already synced at boot.
        return system.ticks_add(now_ms, TIME_SYNC_INTERVAL_MS)

    before_s = None if clock_set else _wall_time_s(system)
    try:
        synced = system.sync_time()
    except Exception:
        synced = False
    if not synced:
        logger.warn("NTP time sync failed", {"clock_was_set": clock_set})
        return system.ticks_add(now_ms, TIME_SYNC_RETRY_MS)

    context = {"clock_was_set": clock_set}
    after_s = None if before_s is None else _wall_time_s(system)
    if before_s is not None and after_s is not None:
        # The unsynced clock kept running since boot, so this jump converts its
        # timestamps on results queued while offline into real times.
        offset_s = after_s - before_s
        context["offset_s"] = offset_s
        if hasattr(module_runtime, "apply_clock_offset"):
            try:
                context["corrected_results"] = module_runtime.apply_clock_offset(offset_s)
            except Exception as exc:
                logger.warn("Queued result time correction failed", {"error": str(exc)})
    logger.info("NTP time synced", context)
    return system.ticks_add(now_ms, TIME_SYNC_INTERVAL_MS)


def _wall_time_s(system):
    if not hasattr(system, "wall_time_s"):
        return None
    try:
        return int(system.wall_time_s())
    except Exception:
        return None


def _clock_is_set(system):
    if not hasattr(system, "clock_is_set"):
        return True
    try:
        return bool(system.clock_is_set())
    except Exception:
        return True


def _watchdog_feed_interval_ms(watchdog, logger):
    if watchdog is None or not hasattr(watchdog, "get_feed_interval_ms"):
        return None
    try:
        interval_ms = watchdog.get_feed_interval_ms()
    except Exception as exc:
        logger.warn("Watchdog feed interval lookup failed", {"error": str(exc)})
        return None
    if interval_ms is None or int(interval_ms) <= 0:
        return None
    return int(interval_ms)


def _radio_off_sleep_available(power_cfg, system, network, sleep_capabilities, min_sleep_ms, logger):
    if power_cfg is None or not getattr(power_cfg, "radio_off_sleep_enabled", False):
        return False
    if network is None or not hasattr(network, "suspend") or not hasattr(system, "light_sleep_ms"):
        logger.warn("Radio-off sleep unsupported by HAL; using regular sleep")
        return False
    if isinstance(sleep_capabilities, dict) and sleep_capabilities.get("lightsleep") is False:
        logger.warn(
            "Radio-off sleep unsupported: light sleep unavailable; using regular sleep",
            {"reason": sleep_capabilities.get("lightsleep_disabled", "no machine.lightsleep")},
        )
        return False
    logger.info("Radio-off light sleep enabled", {"min_sleep_ms": min_sleep_ms})
    return True


def _next_module_due_ms(module_runtime, logger):
    if not hasattr(module_runtime, "get_next_due_ms"):
        return None
    try:
        return module_runtime.get_next_due_ms()
    except Exception as exc:
        logger.warn("Module schedule lookup failed", {"error": str(exc)})
        return None


def _suspend_network(network, logger):
    try:
        network.suspend()
        return True
    except Exception as exc:
        logger.warn("WiFi suspend failed; radio-off sleep disabled", {"error": str(exc)})
        return False


def _sleep(system, watchdog, logger, duration_ms, chunk_ms):
    if not chunk_ms or duration_ms <= chunk_ms:
        system.sleep_ms(duration_ms)
        return

    remaining_ms = duration_ms
    while remaining_ms > 0:
        step_ms = min(remaining_ms, chunk_ms)
        system.sleep_ms(step_ms)
        remaining_ms -= step_ms
        if remaining_ms > 0:
            _feed_watchdog(watchdog, logger)


def _light_sleep(system, watchdog, logger, duration_ms, chunk_ms):
    """Light-sleep for duration_ms in watchdog-safe chunks.

    Returns step stats; light_slept_ms only counts time spent in steps that
    actually slept. Steps that return immediately are covered with regular
    sleep so the loop cadence holds.
    """
    step_limit_ms = chunk_ms or duration_ms
    # Timer interrupts can end a light sleep early, so loop on the deadline
    # but cap iterations in case the tick counter misbehaves.
    max_steps = 4 * (duration_ms // max(1, step_limit_ms) + 1) + 8
    started_ms = system.time_ms()
    stats = {"steps": 0, "effective_steps": 0, "light_slept_ms": 0}
    consecutive_ineffective = 0

    for _ in range(max_steps):
        remaining_ms = duration_ms - system.ticks_diff(system.time_ms(), started_ms)
        if remaining_ms <= 0:
            break

        step_ms = min(remaining_ms, step_limit_ms)
        before_ms = system.time_ms()
        system.light_sleep_ms(step_ms)
        slept_ms = system.ticks_diff(system.time_ms(), before_ms)
        stats["steps"] += 1

        if step_ms > LIGHT_SLEEP_INEFFECTIVE_MS and slept_ms < LIGHT_SLEEP_INEFFECTIVE_MS:
            consecutive_ineffective += 1
            if consecutive_ineffective >= LIGHT_SLEEP_MAX_INEFFECTIVE:
                remaining_ms = duration_ms - system.ticks_diff(system.time_ms(), started_ms)
                if remaining_ms > 0:
                    _sleep(system, watchdog, logger, remaining_ms, chunk_ms)
                break
            system.sleep_ms(step_ms)
        else:
            consecutive_ineffective = 0
            stats["effective_steps"] += 1
            stats["light_slept_ms"] += slept_ms

        _feed_watchdog(watchdog, logger)

    return stats
