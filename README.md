# sensor.avfallsor

Home Assistant integration for [Avfall Sør](https://avfallsor.no) household
waste pickup (Kristiansand / Vennesla, Norway).

Enter your street address and the integration finds your waste pickup schedule
automatically — no need to look up any ID by hand.

[![hacs][hacsbadge]][hacs]

## Installation

### HACS (recommended)
1. Add this repository as a custom repository in HACS (category: Integration).
2. Install **Avfall Sør**.
3. Restart Home Assistant.

### Manual
1. Copy `custom_components/avfallsor/` into your Home Assistant
   `custom_components/` directory.
2. Restart Home Assistant.

## Configuration

Add the integration from the UI:

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Avfall Sør**.
3. Enter your address, e.g. `Kongeveien 1`. Include the house number; you can
   usually omit the municipality.

The integration resolves the address against Avfall Sør's public address
search, then fetches the pickup calendar. One **device** is created for your
address, with one sensor per waste type found for your property:

- Paper (`Papp og papir`)
- Food waste (`Matavfall`)
- Residual waste (`Restavfall`)
- Metal / Glass (`Glass- og metallemballasje`)
- Plastic (`Plastemballasje`)

To change your address later, use **Settings → Devices & Services → Avfall Sør
→ Reconfigure**.

## Sensors

Each sensor is a **date** sensor whose state is the **next pickup date** for
that waste type. Extra attributes:

| Attribute      | Description                                    |
| -------------- | ---------------------------------------------- |
| `days_until`   | Whole days until the next pickup               |
| `upcoming`     | List of all known upcoming pickup dates (ISO)  |
| `garbage_type` | Internal waste type key                        |

### Days until pickup (template example)

If you want a plain "days until" number, use a template sensor on the
`days_until` attribute. Replace the entity id below with your own — with
`has_entity_name`, the id includes the device name, e.g.
`sensor.avfall_sor_kongeveien_1_residual_waste` (check **Developer Tools →
States**):

```yaml
template:
  - sensor:
      - name: Residual waste in days
        state: "{{ state_attr('sensor.avfall_sor_kongeveien_1_residual_waste', 'days_until') }}"
        unit_of_measurement: days
```

## Dashboards

The integration creates a proper device, so its sensors appear automatically
on the **Areas dashboard** (the new experimental/default dashboard) once you
assign the device to an area:

**Settings → Devices & Services → Avfall Sør → (device) → assign an Area.**

To show the days until the next pickup on a tile card, add the `days_until`
attribute to its `state_content`:

```yaml
type: tile
entity: sensor.avfall_sor_kongeveien_1_residual_waste
state_content:
  - state
  - days_until
```

See the `lovelace_example/` folder for more card and automation examples.

## Upgrading from 0.x (breaking changes)

Version 1.0 is a significant modernization:

- **Address-only setup.** The manual `street_id` lookup and the lat/lon
  fallback have been removed from the config flow. Address search now works
  directly against Avfall Sør's JSON API. Existing entries that were
  configured with a `street_id` continue to work; entries relying only on
  lat/lon must be re-added with an address.
- **Sensor state changed** from an integer number of days to the **next
  pickup date** (`device_class: date`). The old day count is now the
  `days_until` attribute. Automations that read the numeric state must be
  updated (see the template example above).
- HTML scraping (and the `beautifulsoup4` / `html5lib` dependencies) has been
  replaced by Avfall Sør's official JSON endpoints.

## Disclaimer

Unofficial. Uses Avfall Sør's public website endpoints, which may change
without notice. Not affiliated with or endorsed by Avfall Sør.

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
