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
| `sensor.*_cook_stage` | Sensor | Cook stage status (entering, running, waiting) |
| `sensor.*_active_recipe` | Sensor | Currently running recipe automation name (or empty) |
| `sensor.*_cook_started` | Sensor | Timestamp when cook started |
| `sensor.*_time_at_temperature` | Sensor | Counting-up timer showing how long at target temperature (H:MM:SS) |
| `sensor.*_online` | Sensor | Device online status (diagnostic) |
| `sensor.*_firmware_version` | Sensor | Firmware version (diagnostic) |
| `sensor.*_temperature_unit` | Sensor | Device temperature unit setting (diagnostic) |
| `number.*_cook_timer` | Number | Cook timer slider (0–72 hours) — used by water heater on turn on |
| `select.*_recipe_selector` | Select | Recipe dropdown — auto-discovers automations labeled `sous_vide` |

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

### `anova_sous_vide.stop_cook`

Stop cooking and turn off the cooker.

```yaml
action: anova_sous_vide.stop_cook
```

### `anova_sous_vide.set_timer`

Set the cook timer while keeping the cooker running at the current target temperature.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `timer` | Yes | Cook timer in seconds |

```yaml
action: anova_sous_vide.set_timer
data:
  timer: 7200
```

### `anova_sous_vide.reset_timer`

Reset the cook timer to zero while keeping the cooker running at the current target temperature.

```yaml
action: anova_sous_vide.reset_timer
```

### `anova_sous_vide.start_selected_recipe`

Trigger the recipe automation currently selected in the recipe selector.

```yaml
action: anova_sous_vide.start_selected_recipe
```

### `anova_sous_vide.cancel_selected_recipe`

Cancel the recipe automation currently selected in the recipe selector.

```yaml
action: anova_sous_vide.cancel_selected_recipe
```

## Recipe Selector

The integration includes a **recipe selector** dropdown that auto-discovers your recipe automations. Instead of creating a separate dashboard card for each recipe, use one compact card with a dropdown.

### Setup

1. Create a label `sous_vide` in HA: **Settings → Labels → + Create Label**, name it `sous_vide`
2. Add the label to each recipe automation: open the automation → **Labels** → add `sous_vide`
3. The `select.*_recipe_selector` entity auto-populates with your labeled automations

### Dashboard card

```yaml
type: entities
title: Sous Vide Recipe
entities:
  - entity: select.anova_precision_cooker_3_0_recipe_selector
    name: Recipe
  - entity: sensor.anova_precision_cooker_3_0_target_temperature
    name: Current Stage Temp
  - entity: sensor.anova_precision_cooker_duration
    name: Time Remaining
  - entity: sensor.anova_precision_cooker_3_0_timer_mode
    name: Timer Status
  - type: button
    name: Start
    icon: mdi:play
    tap_action:
      action: perform-action
      perform_action: anova_sous_vide.start_selected_recipe
  - type: button
    name: Cancel
    icon: mdi:cancel
    tap_action:
      action: perform-action
      perform_action: anova_sous_vide.cancel_selected_recipe
```

## Recipe Examples

### Simple: Steak (55C for 2 hours)

```yaml
actions:
  - action: anova_sous_vide.start_cook
    data:
      temperature: 55
      timer: 7200
  - wait_template: "{{ states('sensor.anova_precision_cooker_3_0_timer_mode') == 'completed' }}"
  - action: notify.persistent_notification
    data:
      message: "Steak is done!"
```

### Multi-stage: Brisket (68C/8hrs then 75C/16hrs)

```yaml
actions:
  - action: anova_sous_vide.start_cook
    data:
      temperature: 68
      timer: 28800
  - action: notify.persistent_notification
    data:
      message: "Stage 1: Cooking at 68C for 8 hours."
  - wait_template: "{{ states('sensor.anova_precision_cooker_3_0_timer_mode') == 'completed' }}"
  - action: anova_sous_vide.start_cook
    data:
      temperature: 75
      timer: 57600
  - action: notify.persistent_notification
    data:
      message: "Stage 2: Cooking at 75C for 16 hours."
  - wait_template: "{{ states('sensor.anova_precision_cooker_3_0_timer_mode') == 'completed' }}"
  - action: notify.persistent_notification
    data:
      message: "Brisket is done! 24-hour cook complete."
```

### Recipe tips

- **No timer helpers needed** — the `cook_time_remaining` sensor automatically counts down on your dashboard when a timer is active
- The device waits until water reaches target temperature before starting the timer countdown
- The device keeps cooking after the timer completes (does not auto-stop) — use `anova_sous_vide.stop_cook` if you want to stop after the final stage
- The `timer_mode` sensor transitions: `idle` → `running` → `completed`

## Development

```bash
# Run tests
python -m pytest tests/ -v
```

**Project decisions & API notes:** see [`docs/PROJECT-STATE.md`](docs/PROJECT-STATE.md)

**Anova developer docs:** <https://developer.anovaculinary.com/docs/intro>
