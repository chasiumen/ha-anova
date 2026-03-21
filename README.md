# ha-anova

Custom Home Assistant integration for **Anova Precision Cooker 3.0** with full control support.

## Features

- **Start / stop cooking** via `water_heater` entity
- **Set target temperature** (25–95 °C) with slider in HA UI
- **Real-time sensors**: water temperature, heater temperature, triac temperature, cook time, cook time remaining, mode, state
- **PAT authentication** (Personal Access Token from Anova app)
- **Push-based updates** via WebSocket — no polling
- **Multi-stage recipes** via HA scripts/automations (set temp → wait for target → cook for duration → change temp → repeat → notify)

## Installation (HACS)

1. In Home Assistant, go to **HACS → Integrations → ⋮ (top right) → Custom repositories**
2. Add this repo URL, category **Integration**
3. Search for **Anova Sous Vide** and install
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration → Anova Sous Vide**
6. Enter your Personal Access Token (from the Anova app: **More → Developer → Personal Access Tokens**)

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
