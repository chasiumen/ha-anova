# ha-anova — project state & decisions

*Last updated: 2026-03-21 (API testing notes added)*

Use this file to resume work after a break. It captures goals, constraints, and agreed approaches (not implementation status).

---

## Goal

- **Remote control** of an **Anova Precision Cooker 3.0** from **Home Assistant** (Web UI / automations):
  - Start / stop cooking (cooking on/off)
  - Set **target temperature**
- Later: **recipe-style** workflows (scripts, automations, or AppDaemon/Node-RED — not a built-in HA “recipe” format for Anova).

**Reference:** [Anova Developer Documentation](https://developer.anovaculinary.com/docs/intro)

---

## Environment

- Home Assistant runs on a **bare-metal VM** (not Docker).
- **HACS is already installed** on this HA instance.

---

## Why a custom integration?

The **stock Home Assistant `anova` integration** (core) only exposes **sensors** (mode, state, temperatures, timers). It does **not** expose controls for setpoint or start/stop. It uses the **`anova-wifi`** library and cloud **WebSocket** auth — same general family as **Wi‑Fi Precision Cookers** in Anova’s docs.

For a **Wi‑Fi** Precision Cooker 3.0, the relevant documentation branch is typically **Precision Cookers (A4/A5, A6/A7)** — **Personal Access Token**, HTTP auth, **WebSocket** commands — not BLE/Mini/Nano unless the device is actually those protocols.

**Verify:** In the Anova app / device info, confirm **Wi‑Fi** and account used for a **Personal Access Token** (per Wi‑Fi docs).

---

## Verified against live API (manual WebSocket tests)

This section records behavior confirmed with a **Personal Access Token** and a **Precision Cooker 3.0** on the account. Do **not** commit real **`cookerId`** values or PATs to the repo.

### Connection

- Endpoint: `wss://devices.anovaculinary.io` with query params **`token`** (PAT, prefix `anova-`) and **`supportedAccessories=APC`** (see [Authentication](https://developer.anovaculinary.com/docs/devices/wifi/authentication)).
- **Postman / clients:** keep `token` and `supportedAccessories` on the **WebSocket URL only**. Commands are sent as **separate JSON messages** after connect — do not put the PAT inside command bodies.

### Discovery

- After connect, messages include **`EVENT_APC_WIFI_LIST`** with your device(s).
- **`cookerId`** is an **opaque string** from that payload (not a UUID you invent). Wrong `cookerId` → **`RESPONSE`** with **`"error": "unauthorized"`**.
- **`type`** for this hardware: **`"a7"`** (third‑gen Wi‑Fi APC; see [device types](https://developer.anovaculinary.com/docs/devices/wifi/authentication)).

### Commands (PAT)

Docs: [Precision Cooker commands](https://developer.anovaculinary.com/docs/devices/wifi/sous-vide-commands).

- **`requestId`:** new **UUID per outbound command** (client-generated; not reused across commands).
- **`CMD_APC_STOP`:** `payload` = `cookerId` + `type` — confirmed **`status": "ok"`**.
- **`CMD_APC_START`:** `payload` = `cookerId`, `type`, `targetTemperature`, `unit` (`C` / `F`), `timer` (seconds). Confirmed **`status": "ok"`**.
- **`timer`: `0` (observed):** treated as **no countdown** / cook until **`CMD_APC_STOP`** (not all public examples use `0`; keep as project convention once validated on-device).

### Home Assistant integration

Implementation should send the same JSON shapes over the authenticated WebSocket (or via `anova-wifi` if it exposes equivalent sends). Store **PAT** and treat **`cookerId`** as sensitive configuration.

---

## Chosen approach

| Topic | Decision |
|--------|----------|
| **Architecture** | **Custom integration** under `custom_components/<domain>/` (control entities / services). |
| **Distribution** | **Option C — HACS** from a **private Git repo** (user already has HACS; avoids manual copy/rsync for every update). |
| **Portability** | Repo is the source of truth; new HA/VM = reinstall from HACS + reconfigure credentials. |
| **Publishing** | **Private repo** — no requirement to publish publicly. |

### Alternatives considered (not selected)

- **Option A:** `git pull` + deploy script (rsync) into `custom_components/` — simpler stack, no HACS metadata; rejected in favor of HACS UI updates.
- **Sidecar service + REST:** HA calls external service — rejected in favor of all-in-HA custom integration.

---

## HACS checklist (when implementing)

1. Repo layout: `custom_components/<domain>/` at repo root (matches HA expectations).
2. Root **`hacs.json`** (and any other files) per [HACS publish docs](https://hacs.xyz/docs/publish/start).
3. Configure **private repo** access in HACS (token / auth per current HACS docs).
4. HA → **HACS → Integrations → Custom repositories** → add URL → category **Integration** → install.
5. Prefer **tags/releases** for clean “Update available” behavior.
6. **Secrets:** Anova credentials via config flow / HA secrets — not committed to the repo.
7. **Unit tests:** Add **`pytest`** coverage with new code (mock WebSocket / library I/O; never commit real PATs into tests). Run tests before releases.

---

## Option A vs C (short)

| | **A — Script deploy** | **C — HACS** (chosen) |
|--|------------------------|------------------------|
| **Pros** | Minimal deps, full control, any Git host | In-UI install/update, familiar workflow |
| **Cons** | SSH + script each update | `hacs.json`, private token, HACS compatibility |

---

## Next steps when resuming

1. ~~Confirm device protocol (Wi‑Fi / WebSocket)~~ — **done:** PAT + WebSocket + `a7` Precision Cooker 3.0.
2. Scaffold `custom_components/<domain>/` (`manifest.json`, `__init__.py`, platforms as needed) and a **`tests/`** layout with **pytest**.
3. Implement auth + outbound commands ( **`anova-wifi`** and/or same WebSocket JSON as above); add **unit tests** for each substantial change.
4. Add **`hacs.json`** and test **Custom repository** install from private GitHub/GitLab.
5. Add entities/services: target temp, start/stop, optional timer mode (`0` vs seconds); then automations for “recipes.”

---

## Related links

- [Anova Developer Documentation — intro](https://developer.anovaculinary.com/docs/intro)
- [HACS — publish / start](https://hacs.xyz/docs/publish/start)
