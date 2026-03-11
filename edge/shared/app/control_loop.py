from edge.shared.app.dev_command_runtime import execute_dev_command


def run_control_loop(
    system,
    presence,
    device_control,
    module_runtime,
    logger,
    config,
    network=None,
    watchdog=None,
    max_iterations=None,
):
    mode = "production"
    heartbeat_interval_ms = config.heartbeat_interval_ms
    dev_poll_interval_ms = config.dev_poll_interval_ms
    module_poll_interval_ms = config.module_assignment_poll_interval_ms
    network_retry_interval_ms = 5000

    next_heartbeat_ms = 0
    next_dev_poll_ms = 0
    next_module_poll_ms = 0
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
        )
        if network is not None and not network_ready["connected"]:
            next_network_retry_ms = network_ready["next_retry_ms"]

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
                    mode = str(metadata.get("mode", mode))
                    heartbeat_interval_ms = max(1000, int(metadata.get("next_heartbeat_ms", heartbeat_interval_ms)))
                    dev_poll_interval_ms = max(500, int(metadata.get("dev_poll_interval_ms", dev_poll_interval_ms)))
                    module_poll_interval_ms = max(
                        1000,
                        int(metadata.get("module_assignment_poll_interval_ms", module_poll_interval_ms)),
                    )

                next_heartbeat_ms = now + heartbeat_interval_ms

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
        sleep_ms = max(50, min(1000, sleep_until - now))
        system.sleep_ms(sleep_ms)
        iterations += 1


def _ensure_network_connected(network, config, logger, now_ms, next_retry_ms, retry_interval_ms):
    if network is None:
        return {"connected": True, "next_retry_ms": next_retry_ms}

    try:
        connected = network.is_connected()
    except Exception as exc:
        logger.warn("Network state check failed", {"error": str(exc)})
        connected = False

    if connected:
        return {"connected": True, "next_retry_ms": now_ms}

    if now_ms < next_retry_ms:
        return {"connected": False, "next_retry_ms": next_retry_ms}

    try:
        network.connect(config.wifi_ssid, config.wifi_password)
        logger.info("WiFi connected", {"ip": network.get_ip()})
        return {"connected": True, "next_retry_ms": now_ms}
    except Exception as exc:
        logger.warn("WiFi reconnect failed", {"error": str(exc)})
        return {"connected": False, "next_retry_ms": now_ms + retry_interval_ms}


def _safe_watchdog_feed(watchdog, logger):
    try:
        watchdog.feed()
    except Exception as exc:
        logger.warn("Watchdog feed failed", {"error": str(exc)})
