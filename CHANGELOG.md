# CHANGELOG


## v1.1.0 (2026-06-09)

### Features

- Add options flow so existing config entries can have their tunable parameters
  (`cache_ttl`, `min_upstream_interval`, `connect_timeout`, `reconnect_delay`)
  adjusted from the HA UI without deleting and re-adding the integration.
  Saving new options triggers an automatic reload of the proxy.

### Performance

- Raise default `cache_ttl` from **5 s → 30 s**. The previous 5 s TTL was
  shorter than typical `solax_modbus` poll intervals (~10–30 s), causing a
  near-zero cache hit rate and routing every request to the dongle upstream.
- Lower default `min_upstream_interval` from **1.0 s → 0.1 s**. With several
  register blocks polled per scan cycle the old 1 s gate serialised an entire
  scan into 6+ seconds; 0.1 s retains burst protection while eliminating the
  per-request latency penalty.


## v1.0.1 (2026-06-08)

### Bug Fixes

- Fix MBAP header size: the proxy read only 6 bytes but parsed 7, raising a
  `struct.error` on every downstream request ("Unhandled exception in
  client_connected_cb") and leaving `solax_modbus` with no response. Now reads
  the full 7-byte MBAP header (incl. unit id) and removes the duplicate
  unit-byte concatenation in downstream/upstream ADU reconstruction.
- Log unexpected downstream handler errors instead of crashing the asyncio
  client callback.


## v1.0.0 (2026-06-08)

### Features

- Initial release of Local Solax ModBus.
- Rebranded and repurposed from the Local Solis/Ginglong Inverter integration
  ([@Rapsssito](https://github.com/Rapsssito/local-solis-ginglong-inverter)).
- Adds an in-Home Assistant Modbus-TCP caching/throttling proxy ("machine in the middle")
  between the `solax_modbus` integration and the inverter's Wi-Fi dongle.
- Single persistent upstream connection to the dongle prevents reconnect storms.
- Register read caching with configurable TTL decouples HA poll rate from dongle load.
- Write pass-through with cache invalidation keeps all control entities fully responsive.
- Brand/plugin-agnostic: works for SolaX, Solis, and any other inverter supported by
  `solax_modbus` over its TCP interface.
