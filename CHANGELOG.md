# CHANGELOG


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
