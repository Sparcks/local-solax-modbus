# CHANGELOG


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
