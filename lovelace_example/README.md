Avfall Sør is a Norwegian service, so these examples use some Norwegian words.

All examples assume an entity created by the integration. With
`has_entity_name`, entity ids include the device (address) name, so yours will
look something like `sensor.avfall_sor_kongeveien_1_residual_waste`. Check
**Developer Tools → States** for your exact entity ids. The six waste types
are `paper`, `bio`, `residual`, `metal`, `plastic`, and `glass`.

Each sensor's **state is the next pickup date**. Two useful attributes:

- `days_until` — whole days until the next pickup
- `upcoming` — list of all known upcoming pickup dates (ISO strings)

## Showing days until pickup on a tile card

The tile card can show the `days_until` attribute next to the date with no
extra dependencies. Note the number is unlabeled (e.g. "Wed, July 15 · 3"):

```yaml
type: tile
entity: sensor.avfall_sor_kongeveien_1_residual_waste
name: Restavfall
state_content:
  - state
  - days_until
```

### Labeled "N days" via a template helper

If you want a clean "3 days" tile, create a template sensor from the
attribute and put a tile on that instead:

```yaml
# configuration.yaml
template:
  - sensor:
      - name: Restavfall om dager
        unique_id: restavfall_days_until
        state: "{{ state_attr('sensor.avfall_sor_kongeveien_1_residual_waste', 'days_until') }}"
        unit_of_measurement: days
        icon: mdi:trash-can
```

```yaml
type: tile
entity: sensor.restavfall_om_dager
```

## Markdown card

For fully custom text (label included), use a markdown card — no custom
resources required:

```yaml
type: markdown
content: >
  **Restavfall:** om {{ state_attr('sensor.avfall_sor_kongeveien_1_residual_waste', 'days_until') }}
  dager ({{ states('sensor.avfall_sor_kongeveien_1_residual_waste') }})
```

## Entities card

The classic entities card cannot show an arbitrary attribute natively; use the
template helper above and add it as a normal row:

```yaml
type: entities
title: Avfall Sør
entities:
  - entity: sensor.avfall_sor_kongeveien_1_residual_waste
    name: Restavfall
  - entity: sensor.restavfall_om_dager
    name: Restavfall om dager
```

## Notifications ("put the bins out")

The sensor state is a date and each sensor exposes `days_until`, so trigger a
reminder the day before pickup. This example flips an input boolean and sends a
notification when residual or food waste is collected tomorrow:

```yaml
input_boolean:
  notify_avfallsor:
    name: Trash notification
    icon: mdi:bell-ring
```

```yaml
automation:
  - id: avfallsor_bins_out
    alias: Reminder to put waste containers out
    trigger:
      - trigger: time
        at: "18:00:00"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.avfall_sor_kongeveien_1_residual_waste', 'days_until') == 1
             or state_attr('sensor.avfall_sor_kongeveien_1_bio', 'days_until') == 1 }}
    action:
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.notify_avfallsor
      - action: notify.my_pushbullet
        data:
          message: Sett ut restavfall og matavfall.

  - id: avfallsor_paper_out
    alias: Reminder to put the paper container out
    trigger:
      - trigger: time
        at: "18:00:15"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.avfall_sor_kongeveien_1_paper', 'days_until') == 1 }}
    action:
      - action: notify.my_pushbullet
        data:
          message: Sett ut papiravfall.
```

> The screenshot below predates the 1.0 rewrite and may not match the current
> entity names.

![Simple](/lovelace_example/avfallsor.PNG)
