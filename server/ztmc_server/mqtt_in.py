"""MQTT 연결. paho 네트워크 스레드에서 받은 메시지를 asyncio 큐로 넘긴다.

aiomqtt 대신 paho를 쓰는 이유: Windows 기본 이벤트 루프(Proactor)에서 aiomqtt가 동작하지 않는다(decisions.md D-004).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

import paho.mqtt.client as mqtt

from .protocol import now_ms

log = logging.getLogger("ztmc.mqtt")

# (topic, payload, 서버 수신 시각 ms)
Inbound = tuple[str, bytes, float]


class MqttBridge:
    def __init__(
        self,
        host: str,
        port: int,
        prefix: str,
        loop: asyncio.AbstractEventLoop,
        on_message: Callable[[Inbound], None],
    ) -> None:
        self.host, self.port, self.prefix = host, port, prefix
        self.connected = False
        self._loop = loop
        self._on_message = on_message
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="ztmc-server", clean_session=True
        )
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=5)

    def start(self) -> None:
        # connect_async: 브로커가 아직 안 떠 있어도 서버는 뜨고, 뒤에서 계속 재접속한다.
        self._client.connect_async(self.host, self.port, keepalive=10)
        self._client.loop_start()
        log.info("mqtt connecting to %s:%d", self.host, self.port)

    def stop(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()

    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> None:
        if self.connected:
            self._client.publish(topic, payload, qos=qos, retain=retain)

    # ---- paho 스레드에서 불림 ----

    def _handle_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            log.warning("mqtt connect failed: %s", reason_code)
            return
        self.connected = True
        client.subscribe(f"{self.prefix}/+/#", qos=1)
        log.info("mqtt connected, subscribed %s/+/#", self.prefix)

    def _handle_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        self.connected = False
        log.warning("mqtt disconnected: %s", reason_code)

    def _handle_message(self, client, userdata, msg: mqtt.MQTTMessage) -> None:
        item: Inbound = (msg.topic, bytes(msg.payload), now_ms())
        self._loop.call_soon_threadsafe(self._on_message, item)
