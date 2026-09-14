# Eclipse SUMO — 8 km micro ring

Unreal is the camera. SUMO is traffic. This Python package is the slot clock
and tidal operator (Kennedy REVLAC, I-88 / Ogden zippers). Do not put SUMO in
`site/` (GitHub Pages lookdev). Do not reimplement Krauss / IDM here.

Tick: **0.25 s**. Radius: **8 km** around Naperville.

## Compile the net

```bash
python3 scripts/build_sumo_net.py
```

Always writes plain XML under `output/sumo/`:

- `naperville.nod.xml` / `naperville.edg.xml` — OSM graph + schematic spines
- `naperville.typ.xml` — arterial types capped at **45 mph**
- `naperville.con.xml` — zipper merges
- `naperville.rou.xml` — vTypes only (SUMO owns car-following)
- `naperville.sumocfg` — `step-length` 0.25
- `facilities.json` — Kennedy `fictional: false`; I-88 / Ogden `fictional: true`

When **netconvert** is on PATH, that command also compiles
`output/sumo/naperville.net.xml`. That compiled net is what live TraCI loads.

## Install Eclipse SUMO

Debian / Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y sumo sumo-tools
export SUMO_HOME=/usr/share/sumo
python3 -m pip install traci
python3 scripts/build_sumo_net.py   # now writes .net.xml
```

`sumo-tools` provides `netconvert`. The Python client is the `traci` package
(optional extra: `pip install -e ".[sumo]"`).

macOS: `brew install sumo`. Windows: the Eclipse SUMO installer, then add
`bin/` to PATH.

Without SUMO, the same XML is still written and `smartcity serve` / pytest run
a **TraCI mock** (posted-speed along edges + slot-pad holds). The mock is not a
car-following engine.

## Live TraCI

After the net exists:

```bash
export SMARTCITY_SUMO=1
smartcity serve --host 127.0.0.1 --port 43147
```

`/ws` publishes live-contract snapshots (`type`, `vehicles[].id/kind/lon/lat/x_m/y_m/speed_mph/heading`, nested `twin`) at 0.25 s. Unreal consumes that. Set `SMARTCITY_SUMO=1`
only when `sumo` and `naperville.net.xml` are present; otherwise the mock loop
is the default.

```bash
smartcity micro --seconds 8          # mock
smartcity micro --seconds 8 --live   # requires SUMO
```

## Docker (default-off)

This file is not a default Compose stack. It does not start with the API.

```bash
python3 scripts/build_sumo_net.py
docker compose -f docker-compose.sumo.yml up --build
```

TraCI port is `127.0.0.1:8813`. Stop with Ctrl-C; nothing else in the repo
depends on this container.

## Tidal lanes in the net

| Facility | In the micro net | API flag | TraCI |
| --- | --- | --- | --- |
| Kennedy REVLAC | schematic reversible extra lanes | `fictional: false` (IDOT) | extra lanes follow inbound 23:00–12:30 weekdays; Friday until 13:30; weekend idle |
| I-88 AV/bus spine | zipper extra lane + ramps | `fictional: true` | inbound 05:00–10:00 |
| Ogden peak travel lane | zipper extra lane, 45 mph | `fictional: true` | inbound 06:30–09:30 |

Slot / AIM pads stay in `smartcity.slots`. SUMO (or the mock) only moves metal.
