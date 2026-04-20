import atexit
import json
import os
import re
import subprocess
import threading
from collections import deque
from contextlib import contextmanager

from config import (DEBUG, INBOUNDS, RUNTIMED_API_HOST, RUNTIMED_API_PORT,
                     RUNTIMED_LOG_DIR, RUNTIMED_PROCESS_NAME, SSL_CERT_FILE,
                     SSL_KEY_FILE)
from logger import logger


class RuntimedConfig(dict):
    """
    Loads Runtimed config json
    config must contain an inbound with the API_INBOUND tag name which handles API requests
    """

    def __init__(self, config: str, peer_ip: str):
        config = json.loads(config)

        self.api_host = RUNTIMED_API_HOST
        self.api_port = RUNTIMED_API_PORT
        self.ssl_cert = SSL_CERT_FILE
        self.ssl_key = SSL_KEY_FILE
        self.peer_ip = peer_ip

        super().__init__(config)
        self._rewrite_panel_log_paths()
        self._apply_error_log_policy()
        self._apply_api()

    def to_json(self, **json_kwargs):
        return json.dumps(self, **json_kwargs)

    def _rewrite_panel_log_paths(self):
        """
        The panel may ship absolute paths under /var/lib/<service>/*.log.
        On a remote node those directories may not exist, so keep logs under
        RUNTIMED_LOG_DIR instead.
        """
        log = self.get("log")
        if not isinstance(log, dict):
            return
        base = RUNTIMED_LOG_DIR.rstrip("/")
        for key, val in list(log.items()):
            if not isinstance(val, str):
                continue
            if not (val.startswith("/var/lib/") and val.endswith(".log")):
                continue
            parts = val.split("/")
            tail = "/".join(parts[4:]) if len(parts) > 4 else os.path.basename(val)
            log[key] = os.path.join(base, tail) if tail else base

    def _apply_error_log_policy(self):
        """
        Without DEBUG, do not send an error log file path to the core (avoids
        e.g. /var/lib/runtimed-node/error.log). infra/conf/log.go then keeps
        error logs on console (stdout), which the node process already reads.
        """
        if DEBUG:
            return
        log = self.get("log")
        if not isinstance(log, dict):
            return
        # Legacy LogConfig.error -> file (see runtimed/infra/conf/log.go)
        log.pop("error", None)
        # If the panel ever sends protobuf-style keys
        for k in ("errorLogPath", "error_log_path"):
            log.pop(k, None)

    def _apply_api(self):
        for inbound in self.get('inbounds', []).copy():
            if inbound.get('protocol') == 'dokodemo-door' and inbound.get('tag') == 'API_INBOUND':
                self['inbounds'].remove(inbound)
                
            elif INBOUNDS and inbound.get('tag') not in INBOUNDS:
                self['inbounds'].remove(inbound)

        for rule in self.get('routing', {}).get("rules", []):
            api_tag = self.get('api', {}).get('tag')
            if api_tag and rule.get('outboundTag') == api_tag:
                self['routing']['rules'].remove(rule)

        self["api"] = {
            "services": [
                "HandlerService",
                "StatsService",
                "LoggerService"
            ],
            "tag": "API"
        }
        self["stats"] = {}
        inbound = {
            "listen": self.api_host,
            "port": self.api_port,
            "protocol": "dokodemo-door",
            "settings": {
                "address": "127.0.0.1"
            },
            "streamSettings": {
                "security": "tls",
                "tlsSettings": {
                    "certificates": [
                        {
                            "certificateFile": self.ssl_cert,
                            "keyFile": self.ssl_key
                        }
                    ]
                }
            },
            "tag": "API_INBOUND"
        }
        try:
            self["inbounds"].insert(0, inbound)
        except KeyError:
            self["inbounds"] = []
            self["inbounds"].insert(0, inbound)

        rule = {
            "inboundTag": [
                "API_INBOUND"
            ],
            "source": [
                "127.0.0.1",
                self.peer_ip
            ],
            "outboundTag": "API",
            "type": "field"
        }
        try:
            self["routing"]["rules"].insert(0, rule)
        except KeyError:
            self["routing"] = {"rules": []}
            self["routing"]["rules"].insert(0, rule)


class RuntimedCore:
    def __init__(self,
                 executable_path: str = "/usr/bin/runtimed",
                 assets_path: str = "/usr/share/runtimed"):
        self.executable_path = executable_path
        self.assets_path = assets_path

        self.version = self.get_version()
        self.process = None
        self.restarting = False

        self._logs_buffer = deque(maxlen=100)
        self._temp_log_buffers = {}
        self._on_start_funcs = []
        self._on_stop_funcs = []
        self._env = {
            "RUNTIMED_LOCATION_ASSET": assets_path,
        }

        atexit.register(lambda: self.stop() if self.started else None)

    def get_version(self):
        cmd = [self.executable_path, "version"]
        output = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT).decode('utf-8')
        m = re.match(r'^Runtimed (\d+\.\d+\.\d+)', output)
        if m:
            return m.groups()[0]

    def __capture_process_logs(self):
        def capture_and_debug_log():
            while self.process:
                output = self.process.stdout.readline()
                if output:
                    output = output.strip()
                    self._logs_buffer.append(output)
                    for buf in list(self._temp_log_buffers.values()):
                        buf.append(output)
                    logger.debug(output)

                elif not self.process or self.process.poll() is not None:
                    break

        def capture_only():
            while self.process:
                output = self.process.stdout.readline()
                if output:
                    output = output.strip()
                    self._logs_buffer.append(output)
                    for buf in list(self._temp_log_buffers.values()):
                        buf.append(output)

                elif not self.process or self.process.poll() is not None:
                    break

        if DEBUG:
            threading.Thread(target=capture_and_debug_log).start()
        else:
            threading.Thread(target=capture_only).start()

    @contextmanager
    def get_logs(self):
        buf = deque(self._logs_buffer, maxlen=100)
        buf_id = id(buf)
        try:
            self._temp_log_buffers[buf_id] = buf
            yield buf
        except (EOFError, TimeoutError):
            pass
        finally:
            del self._temp_log_buffers[buf_id]
            del buf

    @property
    def started(self):
        if not self.process:
            return False

        if self.process.poll() is None:
            return True

        return False

    def start(self, config: RuntimedConfig):
        if self.started is True:
            # Exact string expected by Marzban panel (app/xray/node.py) to
            # trigger its auto-retry via restart(). Do not rename.
            raise RuntimeError("Xray is started already")

        if config.get('log', {}).get('logLevel') in ('none', 'error'):
            config['log']['logLevel'] = 'warning'

        # argv[0] is decoupled from the binary path via `executable=`: the kernel
        # loads self.executable_path, but /proc/PID/cmdline / `ps` show only
        # RUNTIMED_PROCESS_NAME. No "run -config stdin:" flags are passed — the
        # core defaults to reading JSON from stdin when no config.* is present
        # in the working directory.
        self.process = subprocess.Popen(
            [RUNTIMED_PROCESS_NAME],
            executable=self.executable_path,
            env=self._env,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        self.process.stdin.write(config.to_json())
        self.process.stdin.flush()
        self.process.stdin.close()

        self.__capture_process_logs()

        # execute on start functions
        for func in self._on_start_funcs:
            threading.Thread(target=func).start()

    def stop(self):
        if not self.process:
            return

        proc = self.process
        if proc.poll() is not None:
            self.process = None
            return

        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

        self.process = None
        logger.info("Runtimed core stopped")

        # execute on stop functions
        for func in self._on_stop_funcs:
            threading.Thread(target=func).start()

    def restart(self, config: RuntimedConfig):
        if self.restarting is True:
            return

        self.restarting = True
        try:
            logger.info("Restarting Runtimed core...")
            self.stop()
            self.start(config)
        finally:
            self.restarting = False

    def on_start(self, func: callable):
        self._on_start_funcs.append(func)
        return func

    def on_stop(self, func: callable):
        self._on_stop_funcs.append(func)
        return func
