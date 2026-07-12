#!/usr/bin/env python3
"""Generates the visible snorkel parts for every supported vanilla vehicle.

For each vehicle in VEHICLES this writes, under
vehicles/<veh>/universalSnorkel/:

  * snorkel_v10.dae        - three tube meshes (small/medium/tall), objects
                            named snorkel_<veh>_<size>_v10
  * <veh>_snorkel.jbeam   - mount part in the vehicle's "Additional
                            Modification" slot (<veh>_mod) + three tube parts
  * main.materials.json   - the snorkel_black material

Design rules learned the hard way (see docs/HOW_IT_WORKS.md):
  * every tube ends in a short VERTICAL section before the mitre cut, or the
    cut ellipse stretches into a huge blade;
  * flexbody vertex binding requires nodes forming ROUGHLY 90 DEGREE angles
    near every vertex (official flexbodies docs) - a straight line of nodes
    makes the mesh invisible or "weirdly stretched". So the tube skeleton is
    a narrow LADDER: every mast level has an axis node plus an invisible
    node offset sideways, guaranteeing a right-angle pair everywhere;
  * a node level AND a mesh ring every ~0.5 m of mast;
  * beamSpring/beamDamp moderate relative to nodeWeight, or the part goes
    numerically unstable and breaks itself on spawn.

Heights: small = roof-ish (>= 2 m), medium >= 3 m, tall >= 5 m.
Only the D-Series (pickup) coordinates are screenshot-verified; the other
vehicles are first-pass estimates - tweak their entries and re-run.

Run from the repo root:  python3 tools/generate_snorkel_dae.py
"""

import json
import math
import os

VERSION = "v11"
SEGMENTS = 24          # radial resolution of the tubes
TUBE_R = 0.040         # main tube radius (~80 mm OD, typical safari snorkel)
FLARE = 1.12           # slight flare of the mitre opening
BRACKET_R = 0.014
BRACKET_LEN = 0.06     # bracket stub toward the cab
MATERIAL = "snorkel_black"
MITRE_N = (0.0, -0.5, 0.866)  # opening faces forward, tilted

MAST_STEP = 0.5        # a node + mesh ring at least every ~0.5 m of mast

# Path stations per vehicle, in vehicle space (+x left / -x right side,
# +y backward / -y forward, +z up):
#   p0 = engine-bay end above the right fender, p1 = fender edge,
#   p2 = A-pillar base, pm = mid-pillar, rt = A-pillar top / roof line.
# 'pickup' is verified in-game; everything else is a first-pass estimate.
def stations(x, y_bay, z_bay, y_fender, z_fender, y_base, z_base, y_roof, z_roof):
    xo = x + 0.01  # pillar run sits a touch inboard, following the cab taper
    return {
        # start buried inside the fender near the cowl, so the capped lower
        # end of the tube is never visible floating beside the body
        "p0": (round(x + 0.06, 3), round(y_base - 0.30, 3), round(z_base - 0.20, 3)),
        "p1": (x, y_fender, z_fender),
        "p2": (x, y_base, z_base),
        "pm": (xo, (y_base + y_roof) / 2.0, (z_base + z_roof) / 2.0),
        "rt": (xo, y_roof, z_roof),
    }

# vehicles with a vanilla dedicated snorkel slot (<veh>_snorkel): our tubes
# are offered inside that slot, next to the stock snorkel, instead of via the
# Additional Modification mount
NATIVE_SNORKEL_SLOT = {"pickup", "roamer", "van", "hopper"}

VEHICLES = {
    # verified in-game
    "pickup":    stations(-0.99, -1.16, 0.97, -0.92, 1.05, -0.86, 1.30, -0.58, 1.90),
    # same platform as the D-Series
    "roamer":    stations(-0.99, -1.16, 0.97, -0.92, 1.05, -0.86, 1.30, -0.58, 1.90),
    # offroaders / utility
    "hopper":    stations(-0.84, -0.95, 1.00, -0.78, 1.08, -0.72, 1.28, -0.48, 1.75),
    "van":       stations(-0.95, -1.55, 0.95, -1.40, 1.10, -1.30, 1.45, -1.05, 2.05),
    "wydra":     stations(-0.80, -1.00, 0.95, -0.85, 1.05, -0.75, 1.25, -0.50, 1.60),
    # large sedans / classics
    "fullsize":  stations(-0.82, -1.25, 0.88, -1.00, 0.95, -0.55, 1.05, -0.25, 1.42),
    "moonhawk":  stations(-0.83, -1.30, 0.85, -1.05, 0.92, -0.55, 1.02, -0.25, 1.40),
    "barstow":   stations(-0.83, -1.30, 0.85, -1.05, 0.92, -0.55, 1.02, -0.25, 1.38),
    "bluebuck":  stations(-0.83, -1.30, 0.88, -1.05, 0.95, -0.55, 1.05, -0.25, 1.45),
    "burnside":  stations(-0.83, -1.35, 0.95, -1.10, 1.02, -0.60, 1.12, -0.28, 1.55),
    "miramar":   stations(-0.72, -1.10, 0.82, -0.90, 0.88, -0.50, 0.98, -0.22, 1.40),
    "legran":    stations(-0.78, -1.20, 0.85, -0.95, 0.92, -0.52, 1.02, -0.24, 1.40),
    "lansdale":  stations(-0.79, -1.20, 0.87, -0.95, 0.94, -0.52, 1.04, -0.24, 1.45),
    "wendover":  stations(-0.79, -1.20, 0.86, -0.95, 0.93, -0.52, 1.03, -0.24, 1.42),
    "bastion":   stations(-0.79, -1.25, 0.85, -1.00, 0.92, -0.55, 1.02, -0.25, 1.40),
    # compacts / midsize
    "covet":     stations(-0.7, -1.05, 0.78, -0.85, 0.85, -0.48, 0.95, -0.22, 1.35),
    "pessima":   stations(-0.76, -1.15, 0.82, -0.92, 0.89, -0.50, 0.99, -0.23, 1.38),
    "midsize":   stations(-0.76, -1.15, 0.82, -0.92, 0.89, -0.50, 0.99, -0.23, 1.38),
    "sunburst":  stations(-0.76, -1.15, 0.82, -0.92, 0.89, -0.50, 0.99, -0.23, 1.42),
    "vivace":    stations(-0.76, -1.15, 0.83, -0.92, 0.90, -0.50, 1.00, -0.23, 1.43),
    "etk800":    stations(-0.77, -1.20, 0.84, -0.95, 0.91, -0.52, 1.01, -0.24, 1.42),
    "etki":      stations(-0.77, -1.18, 0.83, -0.95, 0.90, -0.52, 1.00, -0.24, 1.40),
    "autobello": stations(-0.64, -0.95, 0.75, -0.80, 0.82, -0.45, 0.92, -0.20, 1.35),
    # low coupes (a snorkel on these is comedy, but it works)
    "etkc":      stations(-0.77, -1.18, 0.80, -0.95, 0.87, -0.52, 0.95, -0.24, 1.32),
    "bolide":    stations(-0.78, -1.10, 0.70, -0.95, 0.77, -0.55, 0.85, -0.28, 1.18),
    "sbr":       stations(-0.78, -1.10, 0.72, -0.95, 0.79, -0.55, 0.87, -0.28, 1.20),
    "scintilla": stations(-0.79, -1.12, 0.72, -0.98, 0.79, -0.58, 0.87, -0.30, 1.20),
}


def tip_heights(z_roof):
    small = max(2.00, round(z_roof + 0.10, 2))
    medium = max(3.00, round(small + 0.50, 2))
    tall = max(5.00, round(medium + 0.50, 2))
    return {"small": small, "medium": medium, "tall": tall}


def mast_ladder(z_roof, z_tip):
    """Brace-node heights between the roof node and the tip, ~MAST_STEP apart."""
    zs = []
    z = z_roof + MAST_STEP
    while z < z_tip - 0.45:
        zs.append(round(z, 2))
        z += MAST_STEP
    if z_tip - (zs[-1] if zs else z_roof) > 0.62:
        zs.append(round(z_tip - MAST_STEP, 2))
    return zs


# --- mesh generation ---------------------------------------------------------

def vsub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vadd(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vscale(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def vlen(a): return math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
def vnorm(a):
    l = vlen(a)
    return (a[0] / l, a[1] / l, a[2] / l)
def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])
def vdot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class MeshBuilder:
    def __init__(self):
        self.positions = []
        self.normals = []
        self.tris = []

    def add_vertex(self, p, n):
        self.positions.append(p)
        self.normals.append(n)
        return len(self.positions) - 1

    def add_tube(self, path, radius, cap_start=True, cap_end=True,
                 end_cut_normal=None, end_flare=1.0):
        tangents = []
        for i in range(len(path)):
            if i == 0:
                t = vsub(path[1], path[0])
            elif i == len(path) - 1:
                t = vsub(path[-1], path[-2])
            else:
                t = vadd(vnorm(vsub(path[i], path[i - 1])),
                         vnorm(vsub(path[i + 1], path[i])))
            tangents.append(vnorm(t))

        rings = []
        for i, (p, t) in enumerate(zip(path, tangents)):
            is_last = i == len(path) - 1
            r = radius * (end_flare if is_last else 1.0)
            ref = (1.0, 0.0, 0.0) if abs(t[0]) < 0.9 else (0.0, 1.0, 0.0)
            u = vnorm(vcross(t, ref))
            w = vnorm(vcross(t, u))
            ring = []
            for s in range(SEGMENTS):
                a = 2 * math.pi * s / SEGMENTS
                n = vadd(vscale(u, math.cos(a)), vscale(w, math.sin(a)))
                vtx = vadd(p, vscale(n, r))
                if is_last and end_cut_normal is not None:
                    dn = vdot(t, end_cut_normal)
                    if abs(dn) > 1e-6:
                        shift = -vdot(vsub(vtx, p), end_cut_normal) / dn
                        vtx = vadd(vtx, vscale(t, shift))
                ring.append(self.add_vertex(vtx, n))
            rings.append(ring)

        for r0, r1 in zip(rings, rings[1:]):
            for s in range(SEGMENTS):
                s2 = (s + 1) % SEGMENTS
                self.tris.append((r0[s], r1[s], r1[s2]))
                self.tris.append((r0[s], r1[s2], r0[s2]))

        for cap, ring_i, flip in ((cap_start, 0, True), (cap_end, -1, False)):
            if not cap:
                continue
            t = tangents[ring_i]
            if ring_i == -1 and end_cut_normal is not None:
                t = vnorm(end_cut_normal)
            n = vscale(t, -1.0) if flip else t
            center = self.add_vertex(path[ring_i], n)
            ring = rings[ring_i]
            for s in range(SEGMENTS):
                s2 = (s + 1) % SEGMENTS
                if flip:
                    self.tris.append((center, ring[s2], ring[s]))
                else:
                    self.tris.append((center, ring[s], ring[s2]))


def build_snorkel(st, z_tip):
    m = MeshBuilder()
    rt = st["rt"]
    mast = [(rt[0], rt[1], z) for z in mast_ladder(rt[2], z_tip)]
    path = [st["p0"], st["p1"], st["p2"], st["pm"], rt] + mast + [(rt[0], rt[1], z_tip)]
    m.add_tube(path, TUBE_R, cap_start=True, cap_end=True,
               end_cut_normal=MITRE_N, end_flare=FLARE)
    # bracket stubs toward the cab, always on the pillar section
    for frac in (0.3, 0.8):
        base = vadd(st["p2"], vscale(vsub(rt, st["p2"]), frac))
        m.add_tube([base, vadd(base, (BRACKET_LEN, 0.0, 0.0))], BRACKET_R,
                   cap_start=False, cap_end=True)
    return m


def fmt_floats(values):
    return " ".join("%.5f" % v for v in values)


def geometry_xml(name, mesh):
    pos = fmt_floats(c for p in mesh.positions for c in p)
    nrm = fmt_floats(c for n in mesh.normals for c in n)
    idx = " ".join("%d %d" % (i, i) for tri in mesh.tris for i in tri)
    count_pos = len(mesh.positions)
    return f"""
    <geometry id="{name}-mesh" name="{name}">
      <mesh>
        <source id="{name}-pos">
          <float_array id="{name}-pos-array" count="{count_pos * 3}">{pos}</float_array>
          <technique_common>
            <accessor source="#{name}-pos-array" count="{count_pos}" stride="3">
              <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <source id="{name}-nrm">
          <float_array id="{name}-nrm-array" count="{count_pos * 3}">{nrm}</float_array>
          <technique_common>
            <accessor source="#{name}-nrm-array" count="{count_pos}" stride="3">
              <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <vertices id="{name}-vtx"><input semantic="POSITION" source="#{name}-pos"/></vertices>
        <triangles material="{MATERIAL}" count="{len(mesh.tris)}">
          <input semantic="VERTEX" source="#{name}-vtx" offset="0"/>
          <input semantic="NORMAL" source="#{name}-nrm" offset="1"/>
          <p>{idx}</p>
        </triangles>
      </mesh>
    </geometry>"""


def node_xml(name):
    return f"""
      <node id="{name}" name="{name}" type="NODE">
        <matrix sid="transform">1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1</matrix>
        <instance_geometry url="#{name}-mesh" name="{name}">
          <bind_material><technique_common>
            <instance_material symbol="{MATERIAL}" target="#{MATERIAL}-material"/>
          </technique_common></bind_material>
        </instance_geometry>
      </node>"""


def dae_document(geoms, nodes):
    return f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <contributor><authoring_tool>generate_snorkel_dae.py</authoring_tool></contributor>
    <unit name="meter" meter="1"/>
    <up_axis>Z_UP</up_axis>
  </asset>
  <library_effects>
    <effect id="{MATERIAL}-effect">
      <profile_COMMON><technique sid="common"><phong>
        <diffuse><color sid="diffuse">0.03 0.03 0.03 1</color></diffuse>
        <specular><color sid="specular">0.15 0.15 0.15 1</color></specular>
        <shininess><float sid="shininess">25</float></shininess>
      </phong></technique></profile_COMMON>
    </effect>
  </library_effects>
  <library_materials>
    <material id="{MATERIAL}-material" name="{MATERIAL}">
      <instance_effect url="#{MATERIAL}-effect"/>
    </material>
  </library_materials>
  <library_geometries>{''.join(geoms)}
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene" name="Scene">{''.join(nodes)}
    </visual_scene>
  </library_visual_scenes>
  <scene><instance_visual_scene url="#Scene"/></scene>
</COLLADA>
"""


# --- jbeam generation --------------------------------------------------------

SIZE_LABELS = {
    "small": ("1. Small Snorkel (roof height, {h} m)", 180),
    "medium": ("2. Medium Snorkel ({h} m)", 220),
    "tall": ("3. Tall Snorkel ({h} m mast)", 260),
}
ANCHOR_EXTRA = {"snb": "e3l", "snf": "e1l", "snp": "e2l", "snr": "e4l"}
OFFSET_X = 0.25   # sideways offset of the invisible ladder-rung nodes (inboard)


def jbeam_part(veh, size, st, z_tip, mesh_name, slot_type):
    rt = st["rt"]
    label_tpl, value = SIZE_LABELS[size]
    label = label_tpl.format(h=("%g" % z_tip))
    # ladder levels: roof, every ~0.5 m of mast, tip
    levels = [rt[2]] + mast_ladder(rt[2], z_tip) + [z_tip]
    axis = []
    for i, z in enumerate(levels):
        if i == 0:
            axis.append(("snr", z))
        elif i == len(levels) - 1:
            axis.append(("snh", z))
        else:
            axis.append((f"sn{i}", z))
    base_nodes = [("snb",) + st["p0"], ("snf",) + st["p1"], ("snp",) + st["p2"]]
    off_x = round(rt[0] + OFFSET_X, 3)

    lines = []
    a = lines.append
    a(f'"{veh}_snorkel_tube_{size}": {{')
    a('    "information":{')
    a('        "authors":"DirtBikeChad",')
    a(f'        "name":"{label}",')
    a(f'        "value":{value},')
    a('    },')
    a(f'    "slotType" : "{slot_type}",')
    a('    "flexbodies": [')
    a('        ["mesh", "[group]:", "nonFlexMaterials"],')
    a(f'        ["{mesh_name}", ["{veh}_snorkel"]],')
    a('    ],')
    a('    "nodes": [')
    a('        ["id", "posX", "posY", "posZ"],')
    a('        {"selfCollision":false},')
    a('        {"collision":true},')
    a('        {"frictionCoef":0.7},')
    a('        {"nodeMaterial":"|NM_PLASTIC"},')
    a(f'        {{"group":"{veh}_snorkel"}},')
    a('        {"nodeWeight":1.2},')
    for n, x, y, z in base_nodes:
        a(f'        ["{n}", {x}, {y}, {z}],')
    for n, z in axis[:-1]:
        a(f'        ["{n}", {rt[0]}, {rt[1]}, {z}],')
    a('        //opening: this node is the functional air intake.')
    a('        //water at or above this point floods the engine.')
    a('        {"engineGroup":["engine_intake"]},')
    a(f'        ["snh", {rt[0]}, {rt[1]}, {z_tip}],')
    a('        {"engineGroup":""},')
    a('        //invisible ladder rungs: the flexbody binder needs nodes forming')
    a('        //~90 degree angles near every vertex; a straight line of nodes')
    a('        //shears the mesh (official flexbodies docs)')
    a('        {"collision":false},')
    for n, z in axis:
        a(f'        ["{n}b", {off_x}, {rt[1]}, {z}],')
    a('        {"collision":true},')
    a('        {"group":""},')
    a('    ],')
    a('    "beams": [')
    a('        ["id1:", "id2:"],')
    a('        {"beamPrecompression":1, "beamType":"|NORMAL"},')
    a('        //--ladder truss structure--')
    a('        {"beamSpring":351000,"beamDamp":120},')
    a('        {"beamDeform":30000,"beamStrength":80000},')
    chain = ["snb", "snf", "snp"] + [n for n, _ in axis]
    for i in range(len(chain) - 1):
        a(f'        ["{chain[i]}","{chain[i+1]}"],')
    for i in range(len(chain) - 2):
        a(f'        ["{chain[i]}","{chain[i+2]}"],')
    a('        ["snb","snr"],')
    offs = [f"{n}b" for n, _ in axis]
    for i in range(len(offs) - 1):
        a(f'        ["{offs[i]}","{offs[i+1]}"],')
    for (n, _), ob in zip(axis, offs):  # rungs
        a(f'        ["{n}","{ob}"],')
    for i in range(len(axis) - 1):      # cross diagonals
        a(f'        ["{axis[i][0]}","{offs[i+1]}"],')
        a(f'        ["{offs[i]}","{axis[i+1][0]}"],')
    a(f'        ["snp","{offs[0]}"],')
    a(f'        ["snf","{offs[0]}"],')
    a('        //--attachment to the engine block--')
    a('        //optional: silently skipped on engines without the standard e1..e4 nodes')
    a('        {"beamSpring":251000,"beamDamp":100},')
    a('        {"beamDeform":25000,"beamStrength":60000},')
    a(f'        {{"breakGroup":"{veh}_snorkel_break"}},')
    a('        {"optional":true},')
    for n in ["snb", "snf", "snp"] + [n for n, _ in axis]:
        for e in ("e1r", "e2r", "e3r", "e4r"):
            a(f'        ["{n}","{e}"],')
        if n in ANCHOR_EXTRA:
            a(f'        ["{n}","{ANCHOR_EXTRA[n]}"],')
    a('        {"optional":false},')
    a('        {"breakGroup":""},')
    a('    ],')
    a('},')
    return "\n".join(lines)


def jbeam_document(veh, st):
    tips = tip_heights(st["rt"][2])
    native = veh in NATIVE_SNORKEL_SLOT
    parts = []
    if not native:
        parts.append(f'''"{veh}_snorkel_mount": {{
    "information":{{
        "authors":"DirtBikeChad",
        "name":"Snorkel (Right A-Pillar)",
        "value":120,
    }},
    "slotType" : "{veh}_mod",
    "slots": [
        ["type", "default", "description"],
        ["{veh}_snorkel_tube", "{veh}_snorkel_tube_small", "Snorkel"],
    ],
}},''')
    slot_type = f"{veh}_snorkel" if native else f"{veh}_snorkel_tube"
    for size in ("small", "medium", "tall"):
        mesh_name = f"snorkel_{veh}_{size}_{VERSION}"
        parts.append(jbeam_part(veh, size, st, tips[size], mesh_name, slot_type))
    return "{\n" + "\n\n".join(parts) + "\n}\n"


MATERIALS = {
    "snorkel_black": {
        "name": "snorkel_black",
        "mapTo": "snorkel_black",
        "class": "Material",
        "version": 1.5,
        "activeLayers": 1,
        "Stages": [
            {"baseColorFactor": [0.05, 0.05, 0.055, 1],
             "metallicFactor": 0.0,
             "roughnessFactor": 0.55},
            {}, {}, {}
        ],
        "translucent": False,
        "castShadows": True
    }
}


def main():
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    for veh, st in VEHICLES.items():
        outdir = os.path.join(root, "vehicles", veh, "universalSnorkel")
        os.makedirs(outdir, exist_ok=True)
        tips = tip_heights(st["rt"][2])
        geoms, nodes = [], []
        for size in ("small", "medium", "tall"):
            name = f"snorkel_{veh}_{size}_{VERSION}"
            mesh = build_snorkel(st, tips[size])
            geoms.append(geometry_xml(name, mesh))
            nodes.append(node_xml(name))
        with open(os.path.join(outdir, f"snorkel_{VERSION}.dae"), "w") as f:
            f.write(dae_document(geoms, nodes))
        with open(os.path.join(outdir, f"{veh}_snorkel.jbeam"), "w") as f:
            f.write(jbeam_document(veh, st))
        with open(os.path.join(outdir, "main.materials.json"), "w") as f:
            json.dump(MATERIALS, f, indent=2)
        print(f"{veh}: tips {tips}")
    print(f"generated {len(VEHICLES)} vehicles")


if __name__ == "__main__":
    main()
