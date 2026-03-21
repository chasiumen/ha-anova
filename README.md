# ha-anova

Custom Home Assistant integration for **Anova Precision Cooker 3.0** with full control support.

## Features

- **Start / stop cooking** via `water_heater` entity
- **Set target temperature** (25–95 °C) with slider in HA UI
- **Real-time sensors**: water temperature, heater temperature, triac temperature, cook time, cook time remaining, mode, state
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
| `water_heater.anova_sous_vide` | Water Heater | Main control — set temp, turn on/off |
| `sensor.anova_sous_vide_water_temperature` | Sensor | Current water temperature |
| `sensor.anova_sous_vide_heater_temperature` | Sensor | Heater element temperature |
| `sensor.anova_sous_vide_triac_temperature` | Sensor | Triac temperature |
| `sensor.anova_sous_vide_cook_time` | Sensor | Elapsed cook time |
| `sensor.anova_sous_vide_cook_time_remaining` | Sensor | Remaining cook time |
| `sensor.anova_sous_vide_mode` | Sensor | Device mode (idle, cook, etc.) |
| `sensor.anova_sous_vide_state` | Sensor | Cook state (preheating, cooking, etc.) |

## Recipe Example (HA Script)

```yaml
sequence:
  - service: water_heater.set_temperature
    target: { entity_id: water_heater.anova_sous_vide }
    data: { temperature: 63 }
  - service: water_heater.turn_on
    target: { entity_id: water_heater.anova_sous_vide }
  - wait_for_trigger:
      - platform: numeric_state
        entity_id: sensor.anova_sous_vide_water_temperature
        above: 63
  - delay: "01:30:00"
  - service: water_heater.set_temperature
    target: { entity_id: water_heater.anova_sous_vide }
    data: { temperature: 66 }
  - wait_for_trigger:
      - platform: numeric_state
        entity_id: sensor.anova_sous_vide_water_temperature
        above: 66
  - delay: "01:30:00"
  - service: water_heater.turn_off
    target: { entity_id: water_heater.anova_sous_vide }
  - service: notify.notify
    data: { message: "Lemon herb chicken is done!" }
```

## Development

```bash
# Run tests
python -m pytest tests/ -v
```

**Project decisions & API notes:** see [`docs/PROJECT-STATE.md`](docs/PROJECT-STATE.md)

**Anova developer docs:** <https://developer.anovaculinary.com/docs/intro>
