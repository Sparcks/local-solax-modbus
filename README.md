# Local Solax ModBus — Modbus-TCP Caching Proxy for Home Assistant<!-- omit in toc -->

Home Assistant integration that acts as a Modbus-TCP caching proxy ("machine in the middle") between the [`solax_modbus`](https://github.com/wills106/homeassistant-solax-modbus) integration and your inverter's Wi-Fi dongle. The proxy holds a single persistent connection to the dongle, rate-limits and caches register reads, and passes writes through immediately — so the dongle is never overloaded while full read **and** write/control functionality is preserved. Works with any inverter supported by `solax_modbus` over its TCP interface (SolaX, Solis, and more). Based on the work of [@wills106](https://github.com/wills106/homeassistant-solax-modbus) & [@Rapsssito](https://github.com/Rapsssito/local-solis-ginglong-inverter).

> **Note:** This is a "vibe-coded" project — built quickly and largely with the help of AI coding assistants. It works for the author's setup but has not been exhaustively tested across devices. Use at your own risk, and please report issues or open PRs if something doesn't work for you.

## Table of Contents<!-- omit in toc -->
- [Installation](#installation)
- [Getting started](#getting-started)
- [Tested devices](#tested-devices)
- [Acknowledgements](#acknowledgements)


## Installation

The easiest way, if you are using [HACS](https://hacs.xyz/), is to install through HACS.

For manual installation, copy all the folders inside `custom_components/` and all of its contents into your Home Assistant's `custom_components` folder. This folder is usually inside your `/config` folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the `custom_components` folder might be located at `/usr/share/hassio/homeassistant`. You may need to create the `custom_components` folder and then copy the folders inside. After copying the folders, restart Home Assistant. You should see the integration in the integrations page.

## Getting started

1. Install the integration through HACS or manually as described above.
2. Configure the integration in Home Assistant. Go to **Settings → Devices & Services → Add Integration → Local Solax ModBus**. Fill in:
   - **Dongle IP address** — the LAN IP of your inverter's Wi-Fi dongle
   - **Dongle Modbus TCP port** — usually `502`
   - **Proxy listen port** — the local port HA will listen on (e.g. `5020`); must not conflict with other services
   - Optional tuning: Cache TTL (default 5 s), Minimum upstream interval (default 1 s), Connect timeout, Reconnect delay
3. In your existing `solax_modbus` integration options, change the TCP **host** to `127.0.0.1` (or your HA machine's IP if `solax_modbus` runs on a different host) and the **port** to the proxy listen port chosen above.
4. Restart Home Assistant if needed. The proxy will connect to the dongle and serve cached register reads to `solax_modbus`. A **Local Solax ModBus Proxy** device will appear with diagnostic sensors (dongle online, cache hit ratio, upstream request count, etc.).

## Tested devices

_This proxy is protocol-transparent and works with any inverter that the `solax_modbus` integration supports over its Modbus TCP interface. The table below tracks confirmed dongle/firmware combinations._

| Inverter / Dongle          | Firmware version | Tested |
| -------------------------- | ---------------- | ------ |
| _Your device here — PRs welcome_ | —           | —      |


## Acknowledgements

This would not be possible without the great work of:
- [@wills106](https://github.com/wills106/homeassistant-solax-modbus) for the `homeassistant-solax-modbus` integration.
- [@Rapsssito](https://github.com/Rapsssito/local-solis-ginglong-inverter) for the original Local Solis/Ginglong Inverter integration that inspired the packaging approach.
- [@planetmarshall](https://github.com/planetmarshall/solis-service) for reverse engineering the Solis/Ginglong datalogger protocol.
