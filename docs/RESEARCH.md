# Research: BeamNG.drive modding & snorkel mechanics

This document records the research that shaped this mod: how BeamNG mods are structured,
how the game decides an engine drowns, what snorkel mods already exist, and why none of
them are universal.

## 1. State of the art: existing snorkel mods

Searching the official repository, forums and community sites turns up only
**per-vehicle** snorkel mods:

| Mod | Vehicle | Mechanism |
|---|---|---|
| [Submarine Mod](https://www.beamng.com/resources/submarine-mod.1949/) | D-Series (Hopper added [later](https://www.beamng.com/resources/submarine-mod.1949/update?update=5644)) | jbeam part: raisable snorkel under *Body → Snorkel* |
| [Lansdale Gambler Snorkel](https://www.beamng.com/resources/lansdale-gambler-snorkel-for-all-versions.27534/) | Gambler 500 | jbeam part on the radiator support slots |
| [Autobello Piccolina Snorkel](https://www.beamng.com/resources/autobello-piccolina-snorkel.38455/) | Piccolina | jbeam part in the engine intake slot |
| [Aurata 1000s pack](https://www.beamng.com/resources/aurata-1000s-engine-exhaust-clutch-and-snorkel.28500/) | Aurata | jbeam part |
| [Waterproof cars pack](https://www.beamng.com/resources/waterproof-cars-pack.1937/) | fixed vanilla list | edited engine jbeams, `waterDamage` line removed |

There is also an old feature-request thread asking for exactly this
([“Snorkel”, beamng.com forums](https://www.beamng.com/threads/snorkel.15086/)) —
a higher air intake for the D15 — which was only ever answered with single-vehicle parts.

**Why they're all single-vehicle:** a jbeam snorkel is a *part*, and a part must plug into
a *slot* defined by one specific vehicle. BeamNG has no "universal slot" shared by all
vehicles, so the jbeam approach fundamentally cannot cover every car — let alone mod cars.
A universal snorkel therefore has to be done in Lua. That's the gap this mod fills.

## 2. How BeamNG decides an engine drowns

From the [official Nodes documentation](https://documentation.beamng.com/modding/vehicle/sections/nodes/)
(section on node groups):

> `engine_intake` — When all the nodes in this group are submerged under water, the
> engine starts flooding with water, until one of them surfaces back up, or the engine
> locks up from the damage.

The intake group is wired to the engine in the engine's jbeam. From the archived official
wiki page for [CombustionEngine](https://wiki.beamng.com/CombustionEngine.html)
(`mainEngine` example, "node beam interface" section):

```json
"waterDamage":  {"[engineGroup]:":["engine_intake"]},
"radiator":     {"[engineGroup]:":["radiator"]},
"engineBlock":  {"[engineGroup]:":["engine_block"]},
```

Key facts that follow from this (and are confirmed by community practice in the
[Waterproof cars pack](https://www.beamng.com/resources/waterproof-cars-pack.1937/) and the
[Facebook/forum discussions](https://www.beamng.com/threads/snorkel.15086/) on snorkels):

1. Flooding starts only when **ALL** intake nodes are underwater. That's why a classic
   snorkel part just adds one more `engine_intake` node up high: as long as that node is
   dry, the engine breathes.
2. Removing the `waterDamage` line makes the engine fully waterproof (the "waterproof
   pack" approach) — but requires editing every engine jbeam of every vehicle.
3. Flooding is *accumulative*: the engine "fills up" over several seconds and can dry out
   if a node surfaces; passing the limit hydrolocks (permanently disables) the engine.
4. Only the intake matters for water damage. Exhaust position is irrelevant to survival,
   and submerged engine-block nodes actually *increase* block cooling (verified in the
   game's `combustionEngineThermals.lua`: `underWaterBlockCoolingCoef` grows for each
   block node for which `obj:inWater(node)` is true).

The flooding state itself lives in the combustion-engine powertrain device inside the
**vehicle Lua VM** (the same place damage like `engineHydrolocked` is raised via
`damageTracker.setDamage("engine", "engineHydrolocked", …)` — verified in the open-source
[BeamLegalRacing](https://github.com/r3eckon/BNG-BeamLegalRacing) mod, which manipulates
exactly these APIs, and in the game's UI which listens for `vehicle.damage.flood`
messages, visible in [RLS Career Overhaul](https://github.com/RLS-Modding/rls_career_overhaul)'s
message app sources). Because it's Lua state updated per graphics frame, another vehicle
extension can legitimately influence it — which is what this mod does.

## 3. How the game resolves `[engineGroup]` references

From the game's own `combustionEngineThermals.lua` (shipped, readable Lua; a copy exists in
the BeamLegalRacing repo):

```lua
for _, n in pairs(jbeamData.engineBlock._engineGroup_nodes) do ... end
arrayConcat(nodes.radiator, jbeamData.radiator._engineGroup_nodes or {})
```

i.e. the jbeam loader resolves `{"[engineGroup]:":["engine_intake"]}` into a list of node
IDs stored under `<property>._engineGroup_nodes`. So the engine's intake nodes are
`jbeamData.waterDamage._engineGroup_nodes`, and node submersion is tested with
`obj:inWater(nodeCid)` — the same call this mod uses for its virtual snorkel tip.

## 4. How BeamNG mods are structured

From the official docs on [correct mod packing](https://documentation.beamng.com/modding/mod-support/mod_packing/)
and [installing mods](https://documentation.beamng.com/tutorials/mods/installing-mods/):

- A mod is a `.zip` dropped into the user folder's `mods/` directory (or an unpacked tree
  under `mods/unpacked/<name>/`). The game loads zips directly.
- The **top level** of the zip must be the game-style content folders — `vehicles/`,
  `levels/`, `lua/`, `scripts/`, `ui/`, `art/` … No extra wrapper folder.

Relevant plumbing, from the official [Extensions documentation](https://documentation.beamng.com/modding/programming/extensions/),
the official blog post [“First Vehicle Lua Mod”](https://blog.beamng.com/first-vehicle-lua-mod/)
and verified against open-source mods ([BeamMP FloodMod](https://github.com/vulcan-dev/BeamMP-FloodMod),
[BeamLegalRacing](https://github.com/r3eckon/BNG-BeamLegalRacing),
[RLS Career Overhaul](https://github.com/RLS-Modding/rls_career_overhaul)):

- **Extensions** live in `lua/ge/extensions/` (game-engine VM) and
  `lua/vehicle/extensions/` (per-vehicle VM). They are plain modules
  (`local M = {} … return M`) and are *not* auto-loaded — something must call
  `extensions.load("name")`.
- **Bootstrap**: `scripts/<modName>/modScript.lua` runs when the mod activates. The
  established pattern (verbatim from the FloodMod):

  ```lua
  load("extensionName")
  registerCoreModule("extensionName")
  ```

- **GE hooks** used here: `onExtensionLoaded()`, `onVehicleSpawned(vehicleId)`. A GE
  extension reaches into a vehicle VM with `veh:queueLuaCommand("...")`, and vehicle Lua
  can call back with `obj:queueGameEngineLua("...")`.
- **Vehicle hooks**: `updateGFX(dt)` per frame, `onReset` on vehicle reset. Vehicle Lua
  exposes `powertrain.getDevice("mainEngine")`, `v.data.nodes` (node table incl.
  positions), `obj:inWater(cid)`, `guihooks.message(...)`, `damageTracker` — all verified
  in the open-source mods above.
- **Custom keybindings**: a JSON in `lua/ge/extensions/core/input/actions/` defines
  actions; `"ctx": "vlua"` makes the command run in the *current vehicle's* Lua VM. Users
  bind the key under Options → Controls. (Pattern from the forum thread
  [“Custom Input LUA for all vehicles”](https://www.beamng.com/threads/custom-input-lua-for-all-vehicles.100080/)
  and the official input actions files.)

## 5. Design decision

Given all of the above, the universal snorkel is implemented as:

1. `scripts/universalSnorkel/modScript.lua` → loads the GE extension at mod activation.
2. GE extension `universalSnorkel` → injects the vehicle extension into every current and
   future vehicle, stores the global mode, persists it to
   `settings/universalSnorkel.json` in the user folder.
3. Vehicle extension `universalSnorkelVehicle` → finds all combustion-engine devices,
   finds the vehicle's highest node (the virtual snorkel opening), and while that node is
   above water (or always, in MAX mode) pins the engine's flood accumulator at zero every
   frame. Flooding takes seconds to fill, so a per-frame reset makes hydrolock
   unreachable; the accumulator field is discovered by name pattern (`*flood*`, numeric)
   to stay robust across game versions.

Trade-off vs. a jbeam part: no visible snorkel mesh, but works on literally every vehicle
with a combustion engine, which is the point of this mod. A guide for building the
classic visible jbeam snorkel for a specific vehicle is included in
[`VISIBLE_SNORKEL_JBEAM_GUIDE.md`](VISIBLE_SNORKEL_JBEAM_GUIDE.md).

## Sources

- https://documentation.beamng.com/modding/vehicle/sections/nodes/ — `engine_intake` group semantics
- https://wiki.beamng.com/CombustionEngine.html (archived) — `waterDamage` jbeam property
- https://documentation.beamng.com/modding/mod-support/mod_packing/ — zip layout
- https://documentation.beamng.com/tutorials/mods/installing-mods/ — installation
- https://documentation.beamng.com/modding/programming/extensions/ — extension system
- https://blog.beamng.com/first-vehicle-lua-mod/ — vehicle Lua hooks (`updateGFX`, `init`, `reset`)
- https://documentation.beamng.com/modding/vehicle/intro_jbeam/ — jbeam introduction
- https://www.beamng.com/threads/custom-input-lua-for-all-vehicles.100080/ — input actions + `ctx: vlua`
- https://github.com/vulcan-dev/BeamMP-FloodMod — modScript bootstrap pattern
- https://github.com/r3eckon/BNG-BeamLegalRacing — vehicle-Lua API usage (`powertrain`, `damageTracker`, `v.data.nodes`), game `combustionEngineThermals.lua`
- https://github.com/RLS-Modding/rls_career_overhaul — `obj:inWater` usage, `vehicle.damage.flood` UI message key
- https://www.beamng.com/resources/submarine-mod.1949/ — prior art (D-Series/Hopper)
- https://www.beamng.com/resources/lansdale-gambler-snorkel-for-all-versions.27534/ — prior art (Gambler)
- https://www.beamng.com/resources/autobello-piccolina-snorkel.38455/ — prior art (Piccolina)
- https://www.beamng.com/resources/aurata-1000s-engine-exhaust-clutch-and-snorkel.28500/ — prior art (Aurata)
- https://www.beamng.com/resources/waterproof-cars-pack.1937/ — prior art (waterproofing by jbeam edit)
- https://www.beamng.com/threads/snorkel.15086/ — original community request
