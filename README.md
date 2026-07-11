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

## Features

- **Three snorkel modes**, cycled with a single keybind, applied to every spawned vehicle:
  - **OFF** — stock behaviour: drive into deep water and the engine floods and hydrolocks.
  - **HIGH** — a virtual roof-level snorkel. Your engine keeps breathing as long as the
    *highest point of the vehicle* is above the waterline. Sink past the roof and it
    floods just like stock. This is the realistic "high snorkel" mode.
  - **MAX** — fully waterproof intake. The engine never hydrolocks, even fully submerged.
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

**Option A — packaged zip (recommended)**

1. Download `UniversalSnorkel.zip` from this repository (or build it, see below).
2. Drop it into your BeamNG mods folder:
   - Windows: `%LocalAppData%\BeamNG.drive\<version>\mods\` (or open it in-game via
     *Repository → Open mods folder*)
3. Start the game (or enable the mod in the Mods menu).

**Option B — unpacked (for tinkering)**

Copy the `lua/` and `scripts/` folders into
`mods/unpacked/universalSnorkel/` inside your user folder, so you end up with
`mods/unpacked/universalSnorkel/lua/...` and `mods/unpacked/universalSnorkel/scripts/...`.

## Usage

1. **Bind the key:** Options → Controls → Vehicle → **"Cycle snorkel mode"** → bind it to
   anything you like (it ships unbound so it can't conflict with your existing bindings).
2. Press the key to cycle **OFF → HIGH → MAX → OFF…**. A message shows the active mode.
3. Drive into the water.

Default mode on first install is **HIGH**.

You can also set the mode from the console (`~` key, make sure "GE-Lua" is selected):

```lua
extensions.universalSnorkel.setGlobalMode("max")   -- "off" | "high" | "max"
extensions.universalSnorkel.getMode()
```

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
- It does not add a visible snorkel mesh (that requires per-vehicle 3D models). It changes
  the *functional* wading depth only.
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
docs/                                                      research + technical docs
build.sh / build.bat                                       zip packagers
```

## License

MIT — see [LICENSE](LICENSE).
