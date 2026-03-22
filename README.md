# ha-anova

Custom Home Assistant integration for **Anova Precision Cooker 3.0** with full control support.

## Features

- **Start / stop cooking** via `water_heater` entity
- **Set target temperature** (25–95 °C) with slider in HA UI
- **Custom service** `anova_sous_vide.start_cook` — set temperature and optional timer in one call
- **Real-time sensors**: water temperature, target temperature, cook time, cook time remaining, mode, timer mode, cook stage, firmware, online status
- **PAT authentication** (Personal Access Token from Anova app)
- **Push-based updates** via WebSocket — no polling
- **Multi-stage recipes** via HA scripts/automations (set temp → wait for target → cook for duration → change temp → repeat → notify)

## Prerequisites

### Getting your Personal Access Token (PAT)

You need a PAT from the Anova app before setting up this integration.

1. Download the **Anova app** on your phone (iOS/Android)
   - Use the **Anova Oven** app (not the older Anova Culinary app) — it works for all devices including sous vide cookers
2. Sign in with the same account your cooker is paired to
3. Navigate to **More → Developer → Personal Access Tokens**
4. Tap **Create Token** — it will generate a token starting with `anova-`
5. Copy the token and save it somewhere safe — you'll need it during setup

> **Note:** The token starts with `anova-`. If your token doesn't start with this prefix, you may be in the wrong section of the app.

## Installation (HACS)

1. In Home Assistant, go to **HACS → Integrations → ⋮ (top right) → Custom repositories**
2. Add this repo URL: `https://github.com/chasiumen/ha-anova`, category **Integration**
3. Search for **Anova Sous Vide** and click **Install**
4. **Restart Home Assistant**
5. Go to **Settings → Devices & Services → + Add Integration**
6. Search for **Anova Sous Vide**
7. Paste your Personal Access Token (the `anova-...` token from the step above)
8. The integration will connect to Anova's WebSocket, discover your cooker, and create all entities automatically

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| `water_heater.anova_*` | Water Heater | Main control — set target temp, turn on/off, current water temp |
| `sensor.*_water_temperature` | Sensor | Current water temperature |
| `sensor.*_target_temperature` | Sensor | Target temperature setpoint |
| `sensor.*_cook_time` | Sensor | Cook timer duration (seconds) |
| `sensor.*_cook_time_remaining` | Sensor | Cook time remaining — real-time countdown (seconds) |
| `sensor.*_timer_mode` | Sensor | Timer state (idle, running, completed) |
| `sensor.*_mode` | Sensor | Device mode (idle, cook, low water, etc.) |
| `sensor.*_cook_stage` | Sensor | Cook stage status (running, waiting) |
| `sensor.*_cook_started` | Sensor | Timestamp when cook started |
| `sensor.*_online` | Sensor | Device online status (diagnostic) |
| `sensor.*_firmware_version` | Sensor | Firmware version (diagnostic) |
| `sensor.*_temperature_unit` | Sensor | Device temperature unit setting (diagnostic) |

## Services

### `anova_sous_vide.start_cook`

Start cooking at a target temperature with an optional timer.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `temperature` | Yes | Target temperature in Celsius (25–95) |
| `timer` | No | Cook timer in seconds (default: 0 = no timer) |

```yaml
action: anova_sous_vide.start_cook
data:
  temperature: 55.0
  timer: 3600
```

## Recipe Example: Brisket (24hrs — 68C/8hrs then 75C/16hrs)

```yaml
actions:
  - variables:
      stage1_temp: 68
      stage1_timer: 28800
      stage2_temp: 75
      stage2_timer: 57600
      timeout_seconds: 7200
  - action: anova_sous_vide.start_cook
    data:
      temperature: "{{ stage1_temp }}"
      timer: "{{ stage1_timer }}"
  - wait_template: >-
      {{ (states('sensor.anova_precision_cooker_3_0_water_temperature') | float(0) - stage1_temp) | abs <= 1 }}
    timeout:
      seconds: "{{ timeout_seconds }}"
    continue_on_timeout: true
  - action: notify.persistent_notification
    data:
      message: "Stage 1: Water at {{ stage1_temp }}C — cooking for 8 hours."
  - delay:
      seconds: "{{ stage1_timer }}"
  - action: anova_sous_vide.start_cook
    data:
      temperature: "{{ stage2_temp }}"
      timer: "{{ stage2_timer }}"
  - wait_template: >-
      {{ (states('sensor.anova_precision_cooker_3_0_water_temperature') | float(0) - stage2_temp) | abs <= 1 }}
    timeout:
      seconds: "{{ timeout_seconds }}"
    continue_on_timeout: true
  - action: notify.persistent_notification
    data:
      message: "Stage 2: Water at {{ stage2_temp }}C — cooking for 16 hours."
  - delay:
      seconds: "{{ stage2_timer }}"
  - action: notify.persistent_notification
    data:
      message: "Brisket is done! 24-hour cook complete."
```

## Development

```bash
# Run tests
python -m pytest tests/ -v
```

**Project decisions & API notes:** see [`docs/PROJECT-STATE.md`](docs/PROJECT-STATE.md)

**Anova developer docs:** <https://developer.anovaculinary.com/docs/intro>
