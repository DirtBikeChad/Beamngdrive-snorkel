# How the Universal Snorkel works

## The vanilla drowning pipeline

1. Every combustion engine's jbeam declares
   `"waterDamage": {"[engineGroup]:":["engine_intake"]}`. The jbeam loader resolves this
   to the list of node IDs whose `engineGroup` contains `engine_intake` (available in the
   vehicle VM as `jbeamData.waterDamage._engineGroup_nodes`).
2. Each graphics frame, the combustion-engine powertrain device checks those nodes with
   `obj:inWater(nodeCid)`. When **all** of them are submerged, a flood accumulator on the
   engine device rises; when at least one node is dry it drains again.
3. If the accumulator reaches its limit, the engine is hydrolocked:
   `damageTracker.setDamage("engine", "engineHydrolocked", …)`, the device is locked up,
   and the UI shows the flood messages (`vehicle.damage.flood` category).

A classic snorkel part beats step 2 by adding a node to the group up high. This mod beats
step 2 at the accumulator instead — which requires no jbeam and therefore works on every
vehicle.

## What this mod does, frame by frame

Component overview:

```
 modScript.lua ──loads──▶ GE: universalSnorkel ──queueLuaCommand──▶ vehicle: universalSnorkelVehicle
                              │  (mode store,                            │  (per-frame protection)
                              │   persistence,                           │
                              ◀──queueGameEngineLua (mode change)────────┘
                              └── onVehicleSpawned → inject into new vehicles
```

Per vehicle, at load:

- **Engine discovery** — every powertrain device of type `combustionEngine` is collected
  (three fallback strategies: `getDevicesByType`, walking `getDevices()`, plain
  `getDevice("mainEngine")`).
- **Flood-field discovery** — instead of hardcoding the accumulator's field name, the mod
  scans the device for numeric fields whose name contains `flood` (case-insensitive).
  This matches the game's naming (cf. `floodLevel`) while tolerating renames. If nothing
  matches, it retries every 2 s and logs a clear warning so failures are visible, not
  silent.
- **Virtual snorkel tip** — the node with the highest Z position in the vehicle's design
  data (`v.data.nodes`) is picked as the snorkel opening. On a pickup that's the cab/roll
  bar, on a sedan the roof line — exactly where a tall snorkel would end.

Per frame (`updateGFX`):

- **OFF** → do nothing (fully stock behaviour).
- **HIGH** → test `obj:inWater(tipNode)`. Above water ⇒ pin every discovered flood field
  on every engine to `0`. Below water ⇒ stand back and let vanilla flooding do its thing
  (with a UI warning on the transition).
- **MAX** → always pin the flood fields to `0`.

Why pinning once per frame is sufficient: flooding is designed to take multiple seconds
of full submersion before hydrolock. Even in the worst-case update ordering the
accumulator can only gain one frame's worth of flooding (a few milliseconds) before being
reset, so it never gets anywhere near the limit.

Why it's safe: the reset is non-destructive (the same field the game itself drains when a
node surfaces), touches nothing else on the device, and never runs in OFF mode. Already
hydrolocked engines are *not* repaired — the mod prevents damage, it doesn't undo it.

## Mode synchronisation & persistence

- The keybind action (`input_actions_universalSnorkel.json`, `ctx: vlua`) calls
  `cycleMode()` on the **current** vehicle, which applies the new mode locally (showing
  the UI message once) and reports it to the GE extension.
- The GE extension persists the mode to `settings/universalSnorkel.json` (user folder,
  via `jsonWriteFile`) and silently re-broadcasts it to all other spawned vehicles.
- `onVehicleSpawned` pushes the extension + current mode into every new vehicle, so
  traffic and newly spawned cars are covered automatically, and `onExtensionLoaded`
  covers vehicles that already exist when the mod loads.

## Failure modes & debugging

Open the console (`~`) and filter for `universalSnorkel`:

- `Universal Snorkel loaded — current mode: 'high'` — GE side is up.
- `Universal Snorkel active on this vehicle — 1 engine(s), tip node cid: 123` — vehicle
  side is up and found everything.
- `No flood accumulator field found on engine 'mainEngine'…` — the game version renamed
  the flood field to something not containing "flood"; protection is inactive. Please
  open an issue with your game version.

Useful console probes (vehicle Lua, select "BeamNG — current vehicle" in the console):

```lua
dump(extensions.universalSnorkelVehicle.getMode())
local e = powertrain.getDevice("mainEngine")
for k, val in pairs(e) do if type(val) == "number" and k:lower():find("flood") then print(k, val) end end
dump(e.jbeamData.waterDamage)   -- the resolved engine_intake node list
```
