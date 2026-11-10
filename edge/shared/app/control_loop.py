from edge.shared.app.dev_command_runtime import execute_dev_command
from edge.shared.app.wall_clock import WallClock


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
TIME_SYNC_FAILURE_LOG_EVERY = 10


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
    clock=None,
    ota_checked=False,
):
    """Run the device main loop.

    ota_checked: the caller already ran an OTA check, so wait one poll interval
    before the next instead of checking again on the first iteration.
    """
    loop = _ControlLoop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        network=network,
        watchdog=watchdog,
        updater=updater,
        clock=clock,
        ota_checked=ota_checked,
    )
    loop.run(max_iterations)


class _ControlLoop:
    """State and steps of the control loop; each iteration services the server, ticks modules, then sleeps."""

    def __init__(
        self,
        system,
        presence,
        device_control,
        module_runtime,
        logger,
        config,
        network,
        watchdog,
        updater,
        clock,
        ota_checked,
    ):
        if clock is None and hasattr(system, "sync_time"):
            clock = WallClock(system)
        self.system = system
        self.presence = presence
        self.device_control = device_control
        self.module_runtime = module_runtime
        self.logger = logger
        self.config = config
        self.network = network
        self.watchdog = watchdog
        self.updater = updater
        self.clock = clock

        self.mode = "production"
        self.heartbeat_interval_ms = config.heartbeat_interval_ms
        self.dev_poll_interval_ms = config.dev_poll_interval_ms
        self.module_poll_interval_ms = config.module_assignment_poll_interval_ms
        self.ota_poll_interval_ms = config.ota_poll_interval_ms

        power_cfg = getattr(config, "power", None)
        self.power_cfg = power_cfg
        self.production_sleep_min_ms = getattr(power_cfg, "production_sleep_min_ms", PRODUCTION_SLEEP_MIN_MS)
        self.production_sleep_max_ms = getattr(power_cfg, "production_sleep_max_ms", PRODUCTION_SLEEP_MAX_MS)
        self.development_sleep_min_ms = getattr(power_cfg, "development_sleep_min_ms", DEVELOPMENT_SLEEP_MIN_MS)
        self.development_sleep_max_ms = getattr(power_cfg, "development_sleep_max_ms", DEVELOPMENT_SLEEP_MAX_MS)
        self.network_retry_base_ms = getattr(power_cfg, "network_retry_base_ms", NETWORK_RETRY_BASE_MS)
        self.network_retry_max_ms = getattr(power_cfg, "network_retry_max_ms", NETWORK_RETRY_MAX_MS)
        self.radio_off_sleep_min_ms = getattr(power_cfg, "radio_off_sleep_min_ms", RADIO_OFF_SLEEP_MIN_MS)

        self.connected = network is None
        self.network_retry_interval_ms = self.network_retry_base_ms
        self.next_network_retry_ms = 0
        self.last_applied_power_mode = None

        self.next_heartbeat_ms = 0
        self.next_dev_poll_ms = 0
        self.next_module_poll_ms = 0
        self.next_ota_poll_ms = system.ticks_add(system.time_ms(), self.ota_poll_interval_ms) if ota_checked else 0
        self.next_time_sync_ms = None

        self.last_dev_revision_hash = None
        self.last_assignment_hash = None

        sleep_capabilities = self._log_sleep_capabilities()
        self._log_wifi_power_save_modes()
        self.radio_off_sleep_enabled = _radio_off_sleep_available(
            power_cfg, system, network, sleep_capabilities, self.radio_off_sleep_min_ms, logger
        )
        self.sleep_chunk_ms = _watchdog_feed_interval_ms(watchdog, logger)
        self.light_sleep_failures = 0

    # ------------------------------------------------------------------ loop

    def run(self, max_iterations=None):
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            if not self._run_once():
                return
            iterations += 1

    def _run_once(self):
        """One loop iteration. Returns False when a module requested a device reset."""
        now = self.system.time_ms()
        if self.clock is not None:
            # Keeps the tick anchor fresh so tick-counter wraparound never matters.
            self.clock.now_ms()
        self._feed_watchdog()

        self._maintain_network(now)
        if self.connected:
            self._service_server(now)
            if self.network is not None:
                self._apply_power_mode()

        if self.module_runtime.tick(now_ms=now).get("reset_requested"):
            return False
        self.logger.tick()

        sleep_ms = self._sleep_duration_ms(now)
        self._feed_watchdog()
        self._sleep(sleep_ms)
        return True

    def _service_server(self, now):
        """Everything that needs the API: runs only while the network is up."""
        if self.network is not None:
            self.next_time_sync_ms = _maybe_sync_time(
                self.clock, self.system, self.logger, now, self.next_time_sync_ms
            )
        self._flush_pending_module_data()
        if self._is_due(now, self.next_heartbeat_ms):
            self._send_heartbeat(now)
        if self._is_due(now, self.next_module_poll_ms):
            self._poll_module_assignment(now)
        if self.updater is not None and self._is_due(now, self.next_ota_poll_ms):
            self._poll_ota_update(now)
        if self.mode == "development" and self._is_due(now, self.next_dev_poll_ms):
            self._poll_dev_command(now)

    # ------------------------------------------------------------------ network

    def _maintain_network(self, now):
        state = _ensure_network_connected(
            network=self.network,
            config=self.config,
            logger=self.logger,
            system=self.system,
            now_ms=now,
            next_retry_ms=self.next_network_retry_ms,
            retry_interval_ms=self.network_retry_interval_ms,
            retry_base_ms=self.network_retry_base_ms,
            retry_max_ms=self.network_retry_max_ms,
        )
        self.connected = state["connected"]
        if self.network is None:
            return
        if self.connected:
            self.network_retry_interval_ms = self.network_retry_base_ms
        else:
            self.next_network_retry_ms = state["next_retry_ms"]
            self.network_retry_interval_ms = state["retry_interval_ms"]

    def _apply_power_mode(self):
        requested = _requested_network_power_mode(self.config, self.mode)
        if requested != self.last_applied_power_mode:
            if _try_apply_network_power_mode(self.network, requested, self.logger):
                self.last_applied_power_mode = requested

    # ------------------------------------------------------------------ server tasks

    def _flush_pending_module_data(self):
        self._call_optional(
            self.module_runtime, "flush_pending_timeout_result", "Pending timeout result flush failed"
        )
        self._call_optional(
            self.module_runtime, "flush_pending_module_status", "Pending module-status flush failed"
        )
        self._call_optional(self.module_runtime, "flush_pending_results", "Pending module result flush failed")

    def _send_heartbeat(self, now):
        try:
            metadata = self.presence.heartbeat_with_metadata()
        except Exception as exc:
            self.logger.warn("Heartbeat poll threw exception", {"error": str(exc)})
            metadata = None

        if isinstance(metadata, dict) and metadata:
            self._apply_heartbeat_metadata(metadata)

        if metadata is not None:
            self.logger.info("Heartbeat sent", {"mode": self.mode, "interval_ms": self.heartbeat_interval_ms})
        self.next_heartbeat_ms = self.system.ticks_add(now, self.heartbeat_interval_ms)
        self._prefetch_upcoming_modules()
        self._feed_watchdog()

    def _apply_heartbeat_metadata(self, metadata):
        server_mode = str(metadata.get("mode", self.mode))
        if server_mode != self.mode:
            self.logger.info("Mode changed", {"from": self.mode, "to": server_mode})
        self.mode = server_mode
        self.heartbeat_interval_ms = max(1000, int(metadata.get("next_heartbeat_ms", self.heartbeat_interval_ms)))
        self.dev_poll_interval_ms = max(500, int(metadata.get("dev_poll_interval_ms", self.dev_poll_interval_ms)))
        self.module_poll_interval_ms = max(
            1000,
            int(metadata.get("module_assignment_poll_interval_ms", self.module_poll_interval_ms)),
        )

    def _prefetch_upcoming_modules(self):
        """Ask the server to prepare code for modules that will run before the next heartbeat."""
        upcoming = self.module_runtime.get_upcoming_modules(next_wake_ms=self.next_heartbeat_ms)
        if not upcoming:
            return
        try:
            self.logger.info(
                "Module prefetch attempt",
                {
                    "source": "imminent_next_loop",
                    "upcoming_count": len(upcoming),
                    "next_heartbeat_ms": self.next_heartbeat_ms,
                    "mode": self.mode,
                },
            )
            if not self.device_control.prefetch_server_code(upcoming):
                self.logger.warn("Module prefetch rejected", {"upcoming_count": len(upcoming)})
        except Exception as exc:
            self.logger.warn("Module prefetch failed", {"error": str(exc)})

    def _poll_module_assignment(self, now):
        try:
            assignment = self.device_control.get_module_assignment(self.last_assignment_hash)
        except Exception as exc:
            self.logger.warn("Module assignment poll threw exception", {"error": str(exc)})
            assignment = None
        if assignment:
            self.last_assignment_hash = assignment.get("assignment_hash", self.last_assignment_hash)
            reconcile = self.device_control.ensure_assigned_modules_present(assignment)
            self.module_runtime.update_assignment(assignment, now_ms=now)
            self.logger.info("Module assignment reconciled", reconcile)
        self.next_module_poll_ms = self.system.ticks_add(now, self.module_poll_interval_ms)
        self._feed_watchdog()

    def _poll_ota_update(self, now):
        try:
            update_info = self.updater.check()
        except Exception as exc:
            self.logger.warn("OTA check threw exception", {"error": str(exc)})
            update_info = None
        if update_info is not None:
            self.logger.info("OTA update available", {"version": update_info.version})
            try:
                self.updater.apply(update_info)
            except Exception as exc:
                self.logger.warn("OTA apply threw exception", {"error": str(exc)})
        self.next_ota_poll_ms = self.system.ticks_add(now, self.ota_poll_interval_ms)
        self._feed_watchdog()

    def _poll_dev_command(self, now):
        try:
            command = self.device_control.get_next_dev_command(self.last_dev_revision_hash)
        except Exception as exc:
            self.logger.warn("Dev command poll threw exception", {"error": str(exc)})
            command = None
        if command and self.device_control.should_execute_dev_command(command, self.last_dev_revision_hash):
            self._run_dev_command(command)
        self.next_dev_poll_ms = self.system.ticks_add(now, self.dev_poll_interval_ms)
        self._feed_watchdog()

    def _run_dev_command(self, command):
        self.last_dev_revision_hash = command.get("revision_hash", self.last_dev_revision_hash)
        result = execute_dev_command(
            system=self.system,
            device_control=self.device_control,
            command=command,
            logger=self.logger,
        )
        self.logger.info(
            "Dev command executed",
            {
                "command_id": command.get("command_id"),
                "revision_hash": self.last_dev_revision_hash,
                "status": result.get("status"),
                "reported": result.get("reported"),
            },
        )

    # ------------------------------------------------------------------ sleep

    def _sleep_duration_ms(self, now):
        """Time until the nearest deadline, clamped to the current mode's sleep bounds."""
        candidates = [self.next_heartbeat_ms, self.next_module_poll_ms]
        if self.network is not None and not self.connected:
            candidates.append(self.next_network_retry_ms)
        if self.mode == "development":
            candidates.append(self.next_dev_poll_ms)
        next_module_due_ms = _next_module_due_ms(self.module_runtime, self.logger)
        if next_module_due_ms is not None:
            candidates.append(next_module_due_ms)

        sleep_until = min(candidates, key=lambda candidate: self.system.ticks_diff(candidate, now))
        remaining_ms = self.system.ticks_diff(sleep_until, now)

        if self.mode == "development":
            return max(self.development_sleep_min_ms, min(self.development_sleep_max_ms, remaining_ms))
        return max(self.production_sleep_min_ms, min(self.production_sleep_max_ms, remaining_ms))

    def _sleep(self, sleep_ms):
        if self.radio_off_sleep_enabled and self.mode != "development" and sleep_ms >= self.radio_off_sleep_min_ms:
            self._radio_off_sleep(sleep_ms)
        else:
            _sleep(self.system, self.watchdog, self.logger, sleep_ms, self.sleep_chunk_ms)

    def _radio_off_sleep(self, sleep_ms):
        """Power the WiFi radio down and light-sleep; falls back to regular sleep if that fails."""
        was_connected = self.connected
        if was_connected:
            # Buffered logs can't be sent while the radio is off, and are lost
            # if the device resets before the next wake.
            _flush_logs(self.logger, "pre_sleep")
        if not _suspend_network(self.network, self.logger):
            self.radio_off_sleep_enabled = False
            _sleep(self.system, self.watchdog, self.logger, sleep_ms, self.sleep_chunk_ms)
            return

        stats = _light_sleep(self.system, self.watchdog, self.logger, sleep_ms, self.sleep_chunk_ms)
        self.logger.info(
            "Radio-off sleep finished",
            {
                "sleep_ms": sleep_ms,
                "light_slept_ms": stats["light_slept_ms"],
                "light_sleep_steps": stats["effective_steps"],
                "steps": stats["steps"],
            },
        )
        self._record_light_sleep_result(stats)
        # Radio power-down resets the driver's power-save mode.
        self.last_applied_power_mode = None
        if was_connected:
            self.next_network_retry_ms = self.system.time_ms()
            self.network_retry_interval_ms = self.network_retry_base_ms

    def _record_light_sleep_result(self, stats):
        if stats["effective_steps"] > 0:
            self.light_sleep_failures = 0
            # The RP2040 RTC stops during light sleep; put the right time back
            # so time.time() inside modules stays correct.
            if self.clock is not None:
                self.clock.restore_system_clock()
            return
        self.light_sleep_failures += 1
        if self.light_sleep_failures >= LIGHT_SLEEP_MAX_INEFFECTIVE:
            self.radio_off_sleep_enabled = False
            self.logger.warn(
                "Light sleep is not sleeping; radio-off sleep disabled",
                {"failed_cycles": self.light_sleep_failures},
            )

    # ------------------------------------------------------------------ helpers

    def _log_sleep_capabilities(self):
        if not hasattr(self.system, "get_sleep_capabilities"):
            return None
        try:
            capabilities = self.system.get_sleep_capabilities()
            self.logger.info("CPU sleep capabilities", capabilities)
            return capabilities
        except Exception as exc:
            self.logger.warn("CPU sleep capability detection failed", {"error": str(exc)})
            return None

    def _log_wifi_power_save_modes(self):
        if self.network is None or not hasattr(self.network, "get_power_save_modes"):
            return
        try:
            self.logger.info("WiFi power-save modes", {"modes": sorted(self.network.get_power_save_modes())})
        except Exception as exc:
            self.logger.warn("WiFi power-save capability detection failed", {"error": str(exc)})

    def _is_due(self, now, deadline_ms):
        return self.system.ticks_diff(now, deadline_ms) >= 0

    def _call_optional(self, target, method_name, failure_message):
        if not hasattr(target, method_name):
            return
        try:
            getattr(target, method_name)()
        except Exception as exc:
            self.logger.warn(failure_message, {"error": str(exc)})

    def _feed_watchdog(self):
        _feed_watchdog(self.watchdog, self.logger)


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


def _maybe_sync_time(clock, system, logger, now_ms, next_sync_ms):
    """Sync the wall clock over NTP while connected; returns the next sync deadline.

    Until NTP has succeeded since boot the time is unset or only taken from the
    RTC (which may be stale), so every loop retries. After that, it refreshes
    once a day and retries a failed refresh after a few minutes.
    """
    if clock is None:
        return next_sync_ms
    if next_sync_ms is not None and system.ticks_diff(now_ms, next_sync_ms) < 0:
        return next_sync_ms

    ntp_synced = clock.is_ntp_synced()
    if next_sync_ms is None and ntp_synced:
        # Already synced at boot.
        return system.ticks_add(now_ms, TIME_SYNC_INTERVAL_MS)

    was_set = clock.is_synced()
    if clock.sync():
        logger.info("NTP time synced", {"clock_was_set": was_set})
        return system.ticks_add(now_ms, TIME_SYNC_INTERVAL_MS)

    failures = clock.sync_failures
    if failures == 1 or failures % TIME_SYNC_FAILURE_LOG_EVERY == 0:
        logger.warn("NTP time sync failed", {"clock_was_set": was_set, "failures": failures})
    if not ntp_synced:
        return now_ms
    return system.ticks_add(now_ms, TIME_SYNC_RETRY_MS)


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
