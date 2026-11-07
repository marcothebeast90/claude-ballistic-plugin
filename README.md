# Long-Range Ballistics

A Claude plugin for long-range rifle shooters and handloaders, covering internal ballistics (loads, pressure, powder, primers, brass, seating depth) and external ballistics (velocity at distance, trajectory, wind, density altitude, spin drift, Coriolis, bullet stability).

## What it does

- **Sorts each question** into internal ballistics, external velocity/energy, external trajectory/zeroing, or stability, and asks only for the data that question needs.
- **Propellant questions**: asks for the powder's production year/lot and checks the producer's current datasheet, because powders can be reformulated under the same name.
- **Bullet questions**: asks for the manufacturer's part number and retrieves that exact bullet's geometry and G1/G7 BC, preferring manufacturer and independently measured data; retailer-only data is labelled as such.
- **Brass**: always asks for brand and primer pocket size (large or small rifle), e.g. for 6.5 Creedmoor, where both exist.
- **Pressure cross-check**: analyses GRT / QuickLOAD output and computes its own interior ballistics model with real powder parameters only, compares to CIP / SAAMI limits, and flags charges above the producer's published maximum.
- **Firing solutions**: point-mass trajectory model with G1/G7, atmosphere, wind, incline, Coriolis/Eötvös and spin drift; output in MRAD and MOA, metric or imperial.
- **Stability**: Miller stability factor and slowest adequate twist.

## Install

- **Claude Code**: `/plugin marketplace add marcothebeast90/claude-ballistic-plugin`, then `/plugin install long-range-ballistics@marcothebeast90-plugins`.
- **Claude apps (claude.ai, desktop, mobile)**: install it from Anthropic's plugin directory once it is listed, or upload the skill folder `skills/long-range-ballistics` as a zip under Customize > Skills.

## Use it

Ask Claude a ballistics question in plain language, for example "is my 6.5 Creedmoor 140 gr still supersonic at 950 m?", "give me a drop chart to 1000 m with 4 m/s wind from 3 o'clock", "is 1:11 twist enough for a 175 gr .308 bullet?" or "is 46 gr of this powder over pressure in my rifle?". The skill loads automatically.

## What it runs, sends and fetches

- **Web lookups**: Claude searches the web and opens powder, bullet and brass manufacturers' pages (and retailer or independent measurement pages as a fallback) to read published data. Only the product names and part numbers in your question are used as search terms.
- **No bundled code**: the plugin contains only Markdown, JSON, a license and an icon. When a calculation is needed, Claude writes Python in its own code sandbox following the equations documented in `skills/long-range-ballistics/references/computation-models.md`. For trajectories it installs the open-source `py-ballisticcalc` package (LGPL-3.0) with pip, only to read the standard G1/G7 drag tables.
- The plugin stores no data and sends nothing to any server of its own.

## Design principles and validation

- Never invents load data, BC values, bullet dimensions or powder parameters; every number comes with its inputs and assumptions.
- A simulation can flag a probable over-pressure; it never certifies a load as safe.
- The documented trajectory model was checked against py-ballisticcalc 3.1.1 (bullet height, velocity and time of flight at 1000 m). The interior ballistics model is a simplified classical model, not validated against instrumented pressure barrels; it is a cross-check, not a substitute for published data.

## Disclaimer

Handloading is potentially dangerous. This plugin is an aid to analysis, not a source of load data. Always start from the producer's published starting load, work up carefully, and stop at the first sign of excessive pressure. The author accepts no liability for the use of this information.

## License

MIT, see `LICENSE`.
