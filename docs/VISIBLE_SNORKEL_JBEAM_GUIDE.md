# Building a *visible* snorkel for a specific vehicle (jbeam guide)

The Lua mod in this repository changes the functional wading depth of every vehicle, but
it cannot draw a snorkel on the body — meshes and part slots are inherently per-vehicle.
If you want the classic visible snorkel on one particular vehicle, this is the
established jbeam recipe (the same one used by the Submarine/Gambler/Piccolina snorkel
mods).

## The one mechanic that matters

The game floods an engine only when **all** nodes of its `engine_intake` engineGroup are
underwater. Add a single extra node to that group at the top of your snorkel tube and the
wading depth becomes "water above the snorkel opening".

## Step by step

1. **Pick a slot.** Find a slot the vehicle already exposes near the fender/A-pillar —
   common choices are the radiator support, body accessory or engine intake slots. List a
   vehicle's slots by opening its jbeam files in
   `<game>/content/vehicles/<vehicle>.zip` (jbeam is plain JSON-ish text).

2. **Create the part file** in your mod at `vehicles/<vehicle>/<vehicle>_snorkel.jbeam`:

```jsonc
{
  "myvehicle_snorkel": {
    "information": {
      "name": "Raised Air Intake (Snorkel)",
      "authors": "you"
    },
    // must match the slot type you picked in step 1:
    "slotType": "myvehicle_intake",

    "flexbodies": [
      ["mesh", "[group]:", "nonFlexMaterials"],
      // your snorkel model, exported as .dae next to the jbeam:
      ["myvehicle_snorkel", ["snorkel"]]
    ],

    "nodes": [
      ["id", "posX", "posY", "posZ"],
      // node weight & group — THE IMPORTANT LINE:
      {"nodeWeight": 1.0},
      {"group": "snorkel"},
      {"engineGroup": ["engine_intake"]},
      // snorkel opening, roughly at A-pillar top height. Coordinates are in
      // metres, vehicle space: X = left/right, Y = front/back, Z = up.
      ["snk1", 0.85, -0.35, 1.55],
      {"engineGroup": ""},
      // a second node lower down to triangulate the tube against the body:
      ["snk2", 0.85, -0.30, 0.95],
      {"group": ""}
    ],

    "beams": [
      ["id1:", "id2:"],
      {"beamSpring": 501000, "beamDamp": 250},
      {"beamDeform": 24000, "beamStrength": 60000},
      ["snk1", "snk2"],
      // tie both nodes into existing body/fender nodes of the vehicle so the
      // snorkel moves and deforms with the body — replace f1r/f2r with real
      // node names from the vehicle's fender jbeam:
      ["snk1", "f1r"], ["snk1", "f2r"],
      ["snk2", "f1r"], ["snk2", "f2r"]
    ]
  }
}
```

3. **Key points**
   - `{"engineGroup": ["engine_intake"]}` before the opening node (and reset with
     `{"engineGroup": ""}` after) is what makes it a functional snorkel. No engine jbeam
     needs editing — engineGroups merge across parts of the same vehicle.
   - The mesh (`flexbodies` entry) is optional — the part works invisibly without it.
     For a real model, author a `.dae` (Blender + the
     [Blender JBeam Editor](https://github.com/angelo234/Blender-JBeam-Editor) helps) and
     map its vertices to the `snorkel` node group.
   - Always anchor new nodes with at least 3 non-collinear beams to existing nodes, or
     they'll flail and spike the physics.

4. **Test in-game:** put the folder in `mods/unpacked/`, spawn the vehicle, open the
   parts selector, fit your part, then check *Debug → Vehicle Debug → Node groups* to
   confirm the opening node shows in `engine_intake`, and drive into water up to the
   opening.

## Why not ship 100 of these in this repo?

Each one needs the target vehicle's real slot names and node names, plus a mesh to look
right — and it still wouldn't cover mod vehicles. That's exactly the gap the Lua-based
universal mod fills. Use this guide when you want the looks on your favourite truck; use
the universal mod for everything else.
