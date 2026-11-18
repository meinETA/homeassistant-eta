<img src="images/header-boilers.webp" alt="ETA boilers" title="ETA PU / PC, SH-P TWIN, eSH-eTWIN" align="right" height="80px"/>
<img src="custom_components/eta_webservices/brand/logo.png" alt="ETA" title="ETA" align="right" height="44px"/>

# ETA Heating for<br>Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/meinETA/homeassistant-eta?style=for-the-badge&label=Release)](https://github.com/meinETA/homeassistant-eta/releases)
[![Downloads](https://img.shields.io/github/downloads/meinETA/homeassistant-eta/total?style=for-the-badge&label=Downloads)](https://github.com/meinETA/homeassistant-eta/releases)
[![Issues](https://img.shields.io/github/issues/meinETA/homeassistant-eta?style=for-the-badge&label=Issues)](https://github.com/meinETA/homeassistant-eta/issues)
[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

[![License: MIT](https://img.shields.io/badge/Licence-MIT-orange.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.5%2B-41BDF5.svg)](https://www.home-assistant.io/)

<a href="https://www.buymeacoffee.com/christofpichler"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-orange.png" alt="Buy me a coffee" height="44"></a>

Home Assistant integration for **ETA heating systems** (pellet, wood, and combined boilers). It reads sensors, states and counters from your ETA unit, and lets you switch and set writable parameters — all discovered automatically over the local [ETA REST API](https://www.meineta.at/javax.faces.resource/downloads/ETA-RESTful-v1.2.pdf.xhtml?ln=default&v=0), no cloud required.

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=meinETA&repository=homeassistant-eta&category=integration)
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=eta_webservices)

### Your plant on the dashboard

Your ETA plant on a dashboard, like on the touch display: detected automatically, with live values, animated pipes and a control tab. See [Plant card](#plant-card).

![Plant card: pellet boiler with storage, buffer, heating circuit and fresh water module](images/plant-card-pellets.png)

| Wood chip boiler | Control tab |
| --- | --- |
| ![Plant card: wood chip boiler with buffer and external demand](images/plant-card-chips.png) | ![Plant card: control tab with boiler, heating circuits and heating times](images/plant-card-control.png) |

## Contents

[Features](#features) · [Plant card](#plant-card) · [Prerequisites](#prerequisites) · [Installation](#installation) · [Moving from the previous repository](#moving-from-the-previous-repository) · [Updating the sensor list](#updating-the-list-of-sensors) · [Error events](#error-events) · [Writable sensors](#writable-sensors) · [Services](#custom-services) · [Energy Dashboard](#integrating-the-eta-unit-into-the-energy-dashboard) · [Troubleshooting](#troubleshooting)

## Features

- **Automatic discovery** of every available endpoint on your ETA unit — with live values shown during setup so you can pick the ones you want.
- **Sensors** for all numeric values (temperatures, pressures, power, flow, counters, …).
- **State sensors** for text states (e.g. `Ready`, `Heating`).
- **Switches** for on/off parameters, detected language-independently.
- **Writable parameters** as `number` entities for setpoints (°C, kg, %, …).
- **Schedules** as `time` entities (API v1.2+).
- **Error monitoring**: a binary sensor for active errors, the active-error count, the latest error message, plus [error events](#error-events) for automations.
- **Services** to write values directly to the unit ([details](#custom-services)).
- **Stable entity identities**: entity ids stay stable across firmware updates, terminal language changes and IP changes.
- **Energy Dashboard** ready ([details](#integrating-the-eta-unit-into-the-energy-dashboard)).

## Plant Card

The integration ships a dashboard card that shows the plant like the ETA touch display: storage, boiler, buffer, heating circuits and fresh water module with live values and animated pipes. No extra installation is needed; the card is loaded automatically.

- **Add it:** edit a dashboard, add a card and pick **ETA Plant**. A panel view gives the best result.
- **Sidebar:** alternatively, show the card as its own sidebar entry, no dashboard needed: `Configure` → **ETA Plant in the sidebar**. On by default for new installations. Admins change name, language and icons there via the gear; the sidebar shows the plant name.
- **Detection:** the plant layout is detected automatically from the selected sensors. If a value is missing on the card, add the matching sensor in the integration options.
- **Control tab:** switch the boiler and heating circuits on or off and select heat, setback or time program. This needs the corresponding switches (e.g. *On/Off button*) to be selected in the integration options.
- **Card settings:** plant (if several are configured), name, language and an icon per block (e.g. the exact boiler model).
- **Report a problem:** if the plant is not shown correctly, use **Open GitHub issue** in the card settings. It opens an issue with an anonymized description of the plant (object numbers, parameter addresses and units only; no names, values or IP addresses). Nothing is sent until the issue is submitted on GitHub, and issues are public.

Layouts that are not covered yet will be added based on reports.

## Screenshots

Every ETA function block becomes a device, and its entities are grouped into the standard Home Assistant cards (Sensors, Configuration, Diagnostic):

<img src="images/devices_overview.png" alt="ETA Heating devices in Home Assistant" width="760">

|            Sensors             |              Diagnostic              |
| :----------------------------- | :----------------------------------- |
| ![Sensors](images/sensors.png) | ![Diagnostic](images/diagnostic.png) |

## Prerequisites

- **Compatibility:** works with any ETA unit that exposes the local webservices/REST API — pellet, wood and combined boilers.
- **Activate the webservices API on your ETA unit first** (see the official [documentation](https://www.meineta.at/javax.faces.resource/downloads/ETA-RESTful-v1.2.pdf.xhtml?ln=default&v=0)):
  - Log in to `meinETA`
  - Go to `Settings` in the **middle** of the page (not the bottom one!)
  - Click `Activate Webservices` and follow the instructions
- **API version 1.2 or higher is recommended.** On older firmware the integration falls back to a compatibility mode where some sensors may not be detected or identified correctly, and writable sensors may not work reliably (v1.1 lacks the endpoints needed to query value details). Firmware files are on `meinETA` (`Settings at the bottom → Installation & Software`).
- **Use a fixed address for the unit.** With stable entity identities a changed IP no longer breaks your entities or history, but the integration still connects to the unit by address — so a static DHCP lease (or a DNS name) keeps it reachable.

## Installation

### Home Assistant Marketplace (2026.11 and newer)

1. Go to **Settings → Marketplace** and search for **ETA Heating**.
2. Click **Install**.
3. Restart Home Assistant.

### HACS (2026.10 and older)

This integration is available in the **HACS default store**.

1. Open **HACS** and search for **ETA Heating** (or use the *Open in HACS* button above).
2. Click **Download**.
3. Restart Home Assistant.

### Manual

1. Copy the `custom_components/eta_webservices` folder into your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.

### Add the integration

Go to **Settings → Devices & Services → Add Integration**, search for **ETA Heating** and follow the steps (or use the *Add integration* button above).

During setup the integration discovers everything on your unit and shows the counts per category, so you can pick exactly what you want (or add everything at once):

<img src="images/setup_choose_entities.png" alt="Choosing entities during setup" width="520">

> **Note:** After you enter host and port, the integration scans every available endpoint once. On large systems (~800 entities) this initial scan can take **8–15 minutes** — please be patient. This only happens when adding the integration or when you explicitly rediscover; normal operation only polls the entities you selected.

## Moving from the Previous Repository

Coming from `Tidone/homeassistant_eta_integration`? Update it to version 1.4.3 first, then follow the [migration guide](docs/migration.md). Your selection, entity IDs, devices and history are restored without a new scan.

## Updating the List of Sensors

If the sensors on the ETA unit change (e.g. new hardware is added), you can refresh the list:

1. Go to `Settings → Devices & Services → ETA Heating`.
2. Click the gear symbol (`Configure`).
3. Choose one of the actions:
   - **Update API & polling settings** — only changes the request limit and update interval.
   - **Update selected entities** — refreshes the values of your selected entities without rediscovering.
   - **Rediscover available entities and update selected entities** — performs a full rediscovery, then lets you review and adjust your selection.
   - **ETA Plant in the sidebar** — shows or hides the [plant card](#plant-card) as its own sidebar entry.

**Maximum parallel API requests** controls how many requests are sent at once. Higher values are faster but put more load on the unit and can cause timeouts on older devices.

- Older ETA units: `3–5`
- Newer ETA units: `8–15` (if stable)
- If you see API errors/timeouts, reduce the value step by step.

## Error Events

The integration publishes an event whenever the ETA terminal reports a new error, or an active error is cleared. These can be handled in automations.

- New error → `eta_webservices_error_detected`
- Cleared error → `eta_webservices_error_cleared`

Each event carries this data:

| Name | Info | Sample Data |
|------------|----------------------------------------------------|---------------------------------------------------------------------------------------------|
| `msg` | Short error message | Water pressure too low 0,00 bar |
| `priority` | Error priority | Error |
| `time` | Time of the error, as reported by the ETA terminal | 2011-06-29T12:48:12 |
| `text` | Detailed error message | Top up heating water! If this warning occurs more than once a year, please contact plumber. |
| `fub` | Functional block of the error | Kessel |
| `host` | Address of the ETA terminal connection | 0.0.0.0 |
| `port` | Port of the ETA terminal connection | 8080 |

### Inspecting a live event

> Only possible while the ETA terminal actually reports an active error.

1. Open Home Assistant in two tabs.
2. Tab 1: `Settings → Devices & Services → Devices → ETA`.
3. Tab 2: `Developer tools → Events`, subscribe to `eta_webservices_error_detected`.
4. Tab 1: click the `Resend Error Events` button.
5. Tab 2: the detailed event info appears.

### Sending a test event

1. `Developer tools → Events`.
2. Event type: `eta_webservices_error_detected`.
3. Event data:
   ```yaml
   msg: Test
   priority: Error
   time: "2023-11-06T12:48:12"
   text: This is a test error.
   fub: Kessel
   host: 0.0.0.0
   port: 8080
   ```
4. Click `Fire Event` — your automation should trigger.

## Writable Sensors

Parameters with a unit of `°C`, `kg` or `%` can be written back to the unit. After adding them via `Configure`, they appear on the ETA device page under **Configuration**.

- The first time you open `Configure` after updating from a version without writable-sensor support, the step takes a while because the integration re-queries the list of valid values from the unit.
- **API v1.1 caveat:** v1.1 lacks the endpoints to query valid value ranges and to tell whether a sensor is writable at all. In compatibility mode the integration guesses the ranges and lists all sensors as potentially writable — you choose the ones that actually are.

> **Caution:** setting a parameter to an invalid value can render your ETA unit unusable. The authors are not responsible for damage caused by writing wrong values.

## Custom Services

The integration provides services to write values to the unit. See the [wiki](https://github.com/meinETA/homeassistant-eta/wiki/Custom-Services) for details.

## Integrating the ETA Unit into the Energy Dashboard

You can add the ETA unit to the Energy Dashboard by converting the total pellet consumption (kg) to energy (kWh) and adding it as a gas source.

Add a template sensor to your `configuration.yaml` (replace the entity id with your own total-consumption sensor). The factor `4.8` is an approximate kWh-per-kg value for wood pellets — adjust it for your fuel:

```yaml
# Convert pellet consumption (kg) to energy consumption (kWh)
template:
  - sensor:
      - name: eta_total_energy
        unit_of_measurement: kWh
        device_class: energy
        state_class: total_increasing
        state: >
          {% set src = states('sensor.eta_kessel_zahlerstande_gesamtverbrauch') %}
          {% if src not in ['unknown', 'unavailable', 'none'] %}
            {{ src | float(0) | multiply(4.8) | round(1) }}
          {% else %}
            {{ src }}
          {% endif %}
```

You can also create the same helper from the UI:

<img src="images/template_sensor.png" alt="Template helper" width="380">

Then add the new sensor to the gas sources of your Energy Dashboard.

## Troubleshooting

Enable verbose logs in the setup dialog (where you enter host and port) to log all communication. After setup, download them at `Settings → System → Logs → Download Full Log`.

> Logs can be large and may contain data from other integrations. Trim the file before sharing it publicly.

## Development

Run the unit tests from the repository root:

```bash
pip3 install -r requirements_test.txt
python3 -m pytest tests/ -v
```

Found a bug or have an idea? Please [open an issue](https://github.com/meinETA/homeassistant-eta/issues).

## Credits

Originally created by [nigl](https://github.com/nigl/homeassistant_eta_integration) and substantially extended by [Tidone](https://github.com/Tidone/homeassistant_eta_integration); now maintained by Tidone and [christofpichler](https://github.com/christofpichler). Built on the ETA REST API.

## License

Released under the [MIT License](LICENSE).

Exception: the icons in `custom_components/eta_webservices/www/icons/` are the property of ETA Heiztechnik GmbH, are not licensed under MIT and may only be used as part of this integration. See the [NOTICE](custom_components/eta_webservices/www/icons/NOTICE) file in that directory. The same applies to the ETA logo in `custom_components/eta_webservices/brand/` and to the plant card screenshots and header image (`images/plant-card-*.png`, `images/header-boilers.webp`), which show these icons.
