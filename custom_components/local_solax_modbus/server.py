"""
Local Solax ModBus — Modbus-TCP caching proxy.

Sits between the solax_modbus integration (downstream clients) and the
inverter Wi-Fi dongle (upstream). Provides:

  - A single persistent upstream TCP connection — no reconnect storms.
  - Request serialisation via asyncio.Lock — no concurrent upstream bursts.
  - Read caching with a configurable TTL (function codes 0x03 and 0x04).
  - Write pass-through with cache invalidation (function codes 0x06 and 0x10).
  - Upstream rate-limiting (minimum interval between successive upstream requests).
  - Automatic reconnect with exponential back-off on upstream disconnect.
  - Multi-client fan-out: any number of HA-side pollers share one dongle connection.
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Modbus TCP ADU layout:
# [transaction_id(2)] [protocol_id(2)=0x0000] [length(2)] [unit_id(1)] [func_code(1)] [data(n)]
_MBAP_HEADER_SIZE = 6
_MIN_ADU_SIZE = 8

# Function codes safe to cache (reads)
_READ_FCS: frozenset[int] = frozenset({0x01, 0x02, 0x03, 0x04})
# Function codes that write — pass through and invalidate cache
_WRITE_FCS: frozenset[int] = frozenset({0x05, 0x06, 0x0F, 0x10})


def _parse_mbap(data: bytes) -> tuple[int, int, int, int]:
    """Return (transaction_id, protocol_id, length, unit_id) from the first 7 bytes."""
    tid, pid, length, uid = struct.unpack_from(">HHHB", data, 0)
    return tid, pid, length, uid


def _replace_tid(adu: bytes, new_tid: int) -> bytes:
    """Return a copy of *adu* with the transaction-id field replaced."""
    return struct.pack(">H", new_tid) + adu[2:]


def _is_exception_response(response: bytes) -> bool:
    """Return True if the response PDU indicates a Modbus exception."""
    if len(response) < 8:
        return False
    return bool(response[7] & 0x80)


@dataclass
class _CacheEntry:
    registers: bytes
    expires_at: float


@dataclass
class ProxyStats:
    """Live counters exposed as HA diagnostic sensors."""

    upstream_requests: int = 0
    downstream_requests: int = 0
    cache_hits: int = 0
    upstream_errors: int = 0
    dongle_online: bool = False
    last_error: str = ""
    _cache_size: int = field(default=0, repr=False)

    @property
    def cache_hit_ratio(self) -> float:
        total = self.cache_hits + self.upstream_requests
        return round(self.cache_hits / total, 3) if total else 0.0


class ModbusTCPProxy:
    """Async Modbus-TCP caching proxy."""

    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        dongle_host: str,
        dongle_port: int,
        cache_ttl: float,
        min_upstream_interval: float,
        connect_timeout: float,
        reconnect_delay: float,
    ) -> None:
        """Initialise proxy with connection parameters."""
        self._listen_host = listen_host
        self._listen_port = listen_port
        self._dongle_host = dongle_host
        self._dongle_port = dongle_port
        self._cache_ttl = cache_ttl
        self._min_upstream_interval = min_upstream_interval
        self._connect_timeout = connect_timeout
        self._reconnect_delay = reconnect_delay

        self._upstream_lock: asyncio.Lock = asyncio.Lock()
        self._upstream_reader: asyncio.StreamReader | None = None
        self._upstream_writer: asyncio.StreamWriter | None = None
        self._last_upstream_time: float = 0.0
        self._upstream_tid: int = 0

        self._cache: dict[tuple[int, int, int, int], _CacheEntry] = {}

        self._server: asyncio.Server | None = None
        self._stopping: bool = False

        self.stats = ProxyStats()

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the proxy server and initiate upstream connection."""
        if self._server is not None:
            return
        self._stopping = False
        self._server = await asyncio.start_server(
            self._handle_downstream,
            self._listen_host,
            self._listen_port,
        )
        _LOGGER.info(
            "Local Solax ModBus proxy listening on %s:%d -> %s:%d",
            self._listen_host,
            self._listen_port,
            self._dongle_host,
            self._dongle_port,
        )
        asyncio.ensure_future(self._ensure_upstream())

    async def stop(self) -> None:
        """Stop proxy and close upstream connection."""
        self._stopping = True
        if self._server is not None:
            self._server.close()
            try:
                await self._server.wait_closed()
            except asyncio.CancelledError:
                pass
            finally:
                self._server = None
        await self._close_upstream()
        _LOGGER.info("Local Solax ModBus proxy stopped")

    # ------------------------------------------------------------------
    # Upstream connection management
    # ------------------------------------------------------------------

    async def _ensure_upstream(self) -> None:
        """Connect to the dongle, retrying with exponential back-off until stopped."""
        delay = self._reconnect_delay
        while not self._stopping:
            if self._upstream_writer is None or self._upstream_writer.is_closing():
                await self._close_upstream()
                try:
                    self._upstream_reader, self._upstream_writer = await asyncio.wait_for(
                        asyncio.open_connection(self._dongle_host, self._dongle_port),
                        timeout=self._connect_timeout,
                    )
                    self.stats.dongle_online = True
                    delay = self._reconnect_delay
                    _LOGGER.info(
                        "Connected to dongle at %s:%d",
                        self._dongle_host,
                        self._dongle_port,
                    )
                except (OSError, asyncio.TimeoutError) as exc:
                    self.stats.dongle_online = False
                    self.stats.last_error = str(exc)
                    _LOGGER.warning(
                        "Cannot connect to dongle at %s:%d - %s. Retrying in %.0fs",
                        self._dongle_host,
                        self._dongle_port,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 60.0)
                    continue
            await asyncio.sleep(2.0)

    async def _close_upstream(self) -> None:
        """Close and clean up the upstream writer."""
        if self._upstream_writer is not None:
            try:
                self._upstream_writer.close()
                await self._upstream_writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._upstream_writer = None
                self._upstream_reader = None
                self.stats.dongle_online = False

    # ------------------------------------------------------------------
    # Downstream client handler
    # ------------------------------------------------------------------

    async def _handle_downstream(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single downstream (HA-side) client connection."""
        addr = writer.get_extra_info("peername")
        _LOGGER.debug("Downstream client connected: %s", addr)
        try:
            while not self._stopping:
                try:
                    header_bytes = await reader.readexactly(_MBAP_HEADER_SIZE)
                except asyncio.IncompleteReadError:
                    break

                tid, pid, length, uid = _parse_mbap(header_bytes)
                if length < 2:
                    _LOGGER.warning("Malformed MBAP from %s (length=%d), dropping", addr, length)
                    break

                pdu_bytes = await reader.readexactly(length - 1)
                adu = header_bytes + bytes([uid]) + pdu_bytes

                self.stats.downstream_requests += 1

                response = await self._dispatch(adu)
                if response is None:
                    _LOGGER.warning("No response for request from %s - upstream unavailable", addr)
                    break

                response = _replace_tid(response, tid)
                writer.write(response)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError, OSError):
            pass
        finally:
            _LOGGER.debug("Downstream client disconnected: %s", addr)
            writer.close()

    # ------------------------------------------------------------------
    # Request dispatch — cache or upstream
    # ------------------------------------------------------------------

    async def _dispatch(self, adu: bytes) -> bytes | None:
        """Return a Modbus response ADU, from cache when possible."""
        if len(adu) < _MIN_ADU_SIZE:
            return None

        unit_id = adu[6]
        func_code = adu[7]

        if func_code in _READ_FCS:
            cache_key = self._cache_key(adu)
            entry = self._cache.get(cache_key)
            if entry is not None and time.monotonic() < entry.expires_at:
                self.stats.cache_hits += 1
                _LOGGER.debug("Cache hit fc=0x%02x unit=%d", func_code, unit_id)
                return self._build_cached_response(adu, entry.registers)

        response = await self._upstream_request(adu)

        if response is not None and func_code in _READ_FCS and not _is_exception_response(response):
            registers = self._extract_data_bytes(response)
            if registers is not None:
                self._cache[self._cache_key(adu)] = _CacheEntry(
                    registers=registers,
                    expires_at=time.monotonic() + self._cache_ttl,
                )
                self.stats._cache_size = len(self._cache)

        if response is not None and func_code in _WRITE_FCS:
            self._invalidate_cache_for_unit(unit_id)

        return response

    # ------------------------------------------------------------------
    # Upstream request (serialised + rate-limited)
    # ------------------------------------------------------------------

    async def _upstream_request(self, adu: bytes) -> bytes | None:
        """Send *adu* upstream and return the raw response ADU, or None on error."""
        async with self._upstream_lock:
            if self._upstream_writer is None or self._upstream_writer.is_closing():
                self.stats.upstream_errors += 1
                return None

            now = time.monotonic()
            wait = self._min_upstream_interval - (now - self._last_upstream_time)
            if wait > 0:
                await asyncio.sleep(wait)

            self._upstream_tid = (self._upstream_tid + 1) & 0xFFFF
            upstream_adu = _replace_tid(adu, self._upstream_tid)

            try:
                self._upstream_writer.write(upstream_adu)
                await self._upstream_writer.drain()
                self._last_upstream_time = time.monotonic()
                self.stats.upstream_requests += 1

                assert self._upstream_reader is not None  # noqa: S101
                resp_header = await asyncio.wait_for(
                    self._upstream_reader.readexactly(_MBAP_HEADER_SIZE),
                    timeout=self._connect_timeout,
                )
                _, _, resp_length, resp_uid = _parse_mbap(resp_header)
                resp_rest = await asyncio.wait_for(
                    self._upstream_reader.readexactly(resp_length - 1),
                    timeout=self._connect_timeout,
                )
                return resp_header + bytes([resp_uid]) + resp_rest

            except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as exc:
                self.stats.upstream_errors += 1
                self.stats.last_error = str(exc)
                self.stats.dongle_online = False
                _LOGGER.warning("Upstream error: %s - reconnecting", exc)
                await self._close_upstream()
                asyncio.ensure_future(self._ensure_upstream())
                return None

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(adu: bytes) -> tuple[int, int, int, int]:
        """Return a cache key based on (unit_id, func_code, start_address, count)."""
        unit_id = adu[6]
        func_code = adu[7]
        if len(adu) >= 12:
            start, count = struct.unpack_from(">HH", adu, 8)
        else:
            start, count = 0, 0
        return (unit_id, func_code, start, count)

    @staticmethod
    def _extract_data_bytes(response: bytes) -> bytes | None:
        """Return raw register bytes from a read response, or None."""
        if len(response) < 9:
            return None
        byte_count = response[8]
        if len(response) >= 9 + byte_count:
            return response[9: 9 + byte_count]
        return None

    @staticmethod
    def _build_cached_response(request_adu: bytes, registers: bytes) -> bytes:
        """Build a synthetic read-response ADU from cached register bytes."""
        tid, pid = struct.unpack_from(">HH", request_adu, 0)
        unit_id = request_adu[6]
        func_code = request_adu[7]
        byte_count = len(registers)
        pdu = bytes([func_code, byte_count]) + registers
        length = 1 + len(pdu)
        return struct.pack(">HHHB", tid, pid, length, unit_id) + pdu

    def _invalidate_cache_for_unit(self, unit_id: int) -> None:
        """Remove all cached entries for *unit_id*."""
        keys_to_remove = [k for k in self._cache if k[0] == unit_id]
        for k in keys_to_remove:
            del self._cache[k]
        if keys_to_remove:
            _LOGGER.debug("Cache invalidated %d entries for unit %d", len(keys_to_remove), unit_id)
        self.stats._cache_size = len(self._cache)
