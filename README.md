# Universal Snorkel for BeamNG.drive

**A snorkel for any and every car.** This mod gives every vehicle in BeamNG.drive
(vanilla *and* modded) a functional snorkel / raised air intake — no jbeam editing,
no per-vehicle parts, one keybind.

Every snorkel mod published so far ([Submarine Mod](https://www.beamng.com/resources/submarine-mod.1949/),
[Gambler snorkel](https://www.beamng.com/resources/lansdale-gambler-snorkel-for-all-versions.27534/),
[Piccolina snorkel](https://www.beamng.com/resources/autobello-piccolina-snorkel.38455/), …)
only works on **one specific vehicle**, because they are jbeam parts that need a slot on
that vehicle. This mod works differently (via Lua, see [How it works](#how-it-works)) so it
applies to **all** vehicles at once — including any mod vehicles you have installed.

The mod has two parts that work together:

1. **The universal system (every car)** — Lua-based, gives any vehicle a virtual snorkel
   in three heights, toggled with one keybind.
2. **A real, visible snorkel for the Gavril D-Series** — shows up in the vehicle config
   parts selector as **"Snorkel"** with **Small / Medium / Tall** tubes, has an actual 3D
   tube + ram head on the right A-pillar, can be ripped off in crashes, and floods the
   engine exactly when the water reaches the ram head opening.

## Features

- **Five snorkel modes**, cycled with a single keybind, applied to every spawned vehicle:
  - **OFF** — stock behaviour: drive into deep water and the engine floods and hydrolocks.
  - **SMALL** — snorkel opening at ~hood height (55% of the vehicle's height).
  - **MEDIUM** — snorkel opening at the roof line (the vehicle's highest point).
  - **TALL** — virtual mast reaching ~1 m above the roof, for properly deep water.
  - **MAX** — fully waterproof intake. The engine never hydrolocks, even fully submerged.

  In SMALL/MEDIUM/TALL the rule is exactly what you'd expect from a real snorkel: **water
  below the opening → engine runs fine; water at or above the opening → the engine starts
  flooding and will hydrolock just like stock.**
- **UI feedback** — on-screen messages when you change mode, when the snorkel goes under,
  and when it surfaces again.
- **Remembers your setting** — the chosen mode is saved to your user folder and restored
  next session, and is automatically applied to every newly spawned vehicle (including
  traffic).
- **Multi-engine support** — vehicles with more than one combustion engine are protected too.
- **Version-tolerant** — the mod discovers the engine's flood state by pattern instead of
  hardcoding one field name, so minor game updates are unlikely to break it. If it ever
  can't find the field it logs a clear warning instead of failing silently.

## Installation

**Option A — download the ready-made zip (recommended)**

1. Download [`UniversalSnorkel.zip`](UniversalSnorkel.zip) from this repository
   (open the file on GitHub → "Download raw file" button). Do **not** unzip it.
2. Drop it into your BeamNG mods folder:
   - Windows: `%LocalAppData%\BeamNG.drive\<version>\mods\` (or open it in-game via
     *Repository → Open mods folder*)
3. Start the game (or enable the mod in the Mods menu). That's it — the D-Series
   "Snorkel" parts are available in the vehicle config right away, and the universal
   (invisible, any-car) system is ready to enable with the keybind or console.

To rebuild the zip yourself, run `./build.sh` / `build.bat`, or just compress the `lua`,
`scripts` and `vehicles` folders into a zip (they must sit at the top level of the zip).

**Option B — unpacked (for tinkering)**

Copy the `lua/`, `scripts/` and `vehicles/` folders into
`mods/unpacked/universalSnorkel/` inside your user folder, so you end up with
`mods/unpacked/universalSnorkel/lua/...` etc.

## Usage

### Universal system (any car)

1. **Bind the key:** Options → Controls → Vehicle → **"Cycle snorkel mode"** → bind it to
   anything you like (it ships unbound so it can't conflict with your existing bindings).
2. Press the key to cycle **OFF → SMALL → MEDIUM → TALL → MAX → OFF…**. A message shows
   the active mode.
3. Drive into the water.

Default mode on first install is **OFF**, so that visible snorkel parts (like the
D-Series ones) decide the wading depth by themselves. Turn a universal mode on when you
want an invisible snorkel on a car that has no snorkel part. Note that an active
universal mode stacks with a fitted snorkel part: whichever protection reaches higher
wins, so leave the universal system OFF when you want the fitted tube to be the limit.

You can also set the mode from the console (`~` key, make sure "GE-Lua" is selected):

```lua
extensions.universalSnorkel.setGlobalMode("medium")  -- "off"|"small"|"medium"|"tall"|"max"
extensions.universalSnorkel.getMode()
```

### Visible snorkel (Gavril D-Series)

1. Spawn any D-Series, open **vehicle config / parts selector** (Ctrl+W or the Vehicle
   Config menu).
2. Find **Additional Modification → "Snorkel (Right A-Pillar)"** and select it.
3. A **"Snorkel"** slot appears — choose **1. Small** (roof height, the default),
   **2. Medium** (~0.8 m above the roof) or **3. Tall** (high mast, ~1.5 m above the
   roof for really deep water).
4. The wading rule is physical: the air intake node sits in the ram head opening at the
   top of the tube. Water below it — engine breathes. Water at or above it — the engine
   floods and starts hydrolocking, exactly like stock deep-water behaviour.

Tip: when driving the D-Series with the visible snorkel, set the universal system to
**OFF** so the wading depth is governed purely by the part you fitted — otherwise the
universal system (if set higher) also protects the engine.

The part is anchored to the engine block with breakable attachment beams, so a rollover
or a tree strike can tear the snorkel off — after that, deep water is your enemy again.

## How it works

Short version (the full research write-up is in [`docs/RESEARCH.md`](docs/RESEARCH.md) and
the technical deep-dive in [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md)):

- BeamNG marks certain engine nodes as the air intake via the jbeam property
  `"waterDamage": {"[engineGroup]:":["engine_intake"]}`. Per the
  [official docs](https://documentation.beamng.com/modding/vehicle/sections/nodes/), when
  **all** nodes in that group are underwater the engine starts flooding until it
  hydrolocks. Classic snorkel mods simply add one extra `engine_intake` node higher up —
  which is why each one only fits a single vehicle.
- This mod instead runs a small extension inside every vehicle's Lua VM. While the
  virtual snorkel is above water it holds the engine's flood accumulator at zero, so the
  hydrolock threshold can never be reached. In **HIGH** mode the "snorkel opening" is the
  vehicle's highest node (found automatically from the node positions), and its
  submersion is tested every frame with the game's own `obj:inWater()` — so the wading
  limit is exactly "water above the roof line", per vehicle, on any vehicle.
- A GE-side extension injects the vehicle extension into every spawned vehicle
  (`onVehicleSpawned`), broadcasts mode changes, and persists your setting.

Want a *visible* snorkel with a real high intake node on a specific vehicle? That's a
per-vehicle jbeam part by nature — see
[`docs/VISIBLE_SNORKEL_JBEAM_GUIDE.md`](docs/VISIBLE_SNORKEL_JBEAM_GUIDE.md) for a
step-by-step guide with a complete example part.

## Building the zip

```bash
./build.sh          # Linux/macOS/Git Bash → dist/UniversalSnorkel.zip
build.bat           # Windows
```

The zip contains `lua/` and `scripts/` at the top level, which is the
[correct packing layout](https://documentation.beamng.com/modding/mod-support/mod_packing/)
for BeamNG mods.

## Compatibility & limitations

- Built and tested against the BeamNG.drive 0.3x-era Lua API (verified against current
  official documentation and several actively maintained open-source mods). This mod has
  **not** been run in-game by its author yet — if something misbehaves, check the console
  (`~`) for `universalSnorkel` log lines and please open an issue with them.
- The universal system changes the *functional* wading depth only (no mesh — that's
  per-vehicle by nature). The visible snorkel with the 3D tube currently exists for the
  Gavril D-Series; other vehicles can be added the same way (see
  [`docs/VISIBLE_SNORKEL_JBEAM_GUIDE.md`](docs/VISIBLE_SNORKEL_JBEAM_GUIDE.md)).
- Exhaust, electrics and drivetrain are unaffected — in BeamNG only the intake
  (`engine_intake` group) causes water damage, and water actually helps cool the block.
- Works in singleplayer; on BeamMP it affects your own vehicles client-side.
- An engine that has **already** hydrolocked stays dead — the mod prevents flooding, it
  doesn't repair damage. Toggle to HIGH/MAX *before* diving.

## Repository layout

```
lua/ge/extensions/universalSnorkel.lua                     GE-side coordinator
lua/ge/extensions/core/input/actions/input_actions_universalSnorkel.json   keybind action
lua/vehicle/extensions/universalSnorkelVehicle.lua         per-vehicle protection logic
scripts/universalSnorkel/modScript.lua                     mod bootstrap
vehicles/pickup/universalSnorkel/pickup_snorkel.jbeam      D-Series visible snorkel parts
vehicles/pickup/universalSnorkel/snorkel.dae               3D meshes (small/medium/tall)
vehicles/pickup/universalSnorkel/main.materials.json       snorkel material
tools/generate_snorkel_dae.py                              mesh generator (edit + re-run)
docs/                                                      research + technical docs
build.sh / build.bat                                       zip packagers
```

The visible part placement was derived from real D-Series-class dimensions; if the tube
sits slightly off your cab, all coordinates live in plain text — tweak the `P0…PATHS`
constants in `tools/generate_snorkel_dae.py`, re-run it, and mirror the same numbers in
`pickup_snorkel.jbeam` (the `snb/snk/snp/snt/snh` node lines).

## License

MIT — see [LICENSE](LICENSE).
