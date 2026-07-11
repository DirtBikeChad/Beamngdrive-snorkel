#!/usr/bin/env python3
"""Generates the snorkel meshes (snorkel.dae) for the D-Series parts.

Produces one COLLADA file containing three objects (snorkel_small,
snorkel_medium, snorkel_tall), each a tube that runs from the engine bay,
over the right fender and up the A-pillar, ending in a flared, forward-facing
mitre-cut opening (the classic 4x4 snorkel top). The tall version continues
as a vertical mast well above the roof line. Also adds two bracket stubs
toward the cab.

Heights: small = roof, medium = ~0.55 m above roof, tall = ~1.1 m above roof.

Run from the repo root:  python3 tools/generate_snorkel_dae.py
Output: vehicles/pickup/universalSnorkel/snorkel.dae
"""

import math
import os

SEGMENTS = 24          # radial resolution of the tubes
TUBE_R = 0.040         # main tube radius (~80 mm OD, typical safari snorkel)
FLARE = 1.12           # slight flare of the mitre opening
BRACKET_R = 0.014
BRACKET_LEN = 0.06     # bracket stub toward the cab
MATERIAL = "snorkel_black"

# Path stations in vehicle space (x right(-)/left(+), y front(-)/rear(+), z up)
# The tube climbs the fender and the A-pillar rake, and always ends in a
# short VERTICAL section before the mitre cut — a slanted final segment
# stretches the cut ellipse into a huge blade shape (looked like a black
# triangle in-game), a vertical one gives a clean 45-degree opening.
P0 = (-0.90, -1.16, 0.97)      # engine-bay end, above/behind right fender area
P1 = (-0.99, -0.92, 1.05)      # over the fender edge, ahead of the door seam
P2 = (-0.99, -0.86, 1.30)      # A-pillar base (bottom corner of the windshield)
PM = (-0.985, -0.73, 1.55)     # mid-pillar, following the pillar rake
RT = (-0.98, -0.58, 1.90)      # A-pillar top / roof line

TIP_SMALL = (-0.98, -0.58, 2.00)    # roof height
TIP_MEDIUM = (-0.98, -0.58, 2.45)   # ~0.55 m above the roof
TIP_TALL = (-0.98, -0.58, 3.00)     # ~1.1 m above the roof — deep wading mast
# opening faces forward, tilted (mitre-cut like real 4x4 snorkels)
MITRE_N = (0.0, -0.5, 0.866)

# every size shares the same fender/pillar run and ends in a vertical mast,
# so all three get the identical clean mitre opening
PATHS = {
    "small": [P0, P1, P2, PM, RT, TIP_SMALL],
    "medium": [P0, P1, P2, PM, RT, TIP_MEDIUM],
    "tall": [P0, P1, P2, PM, RT, TIP_TALL],
}

# bumped whenever mesh/node layout changes: new object names force BeamNG to
# rebuild its mesh/binding cache instead of pairing new meshes with stale data
OBJ_SUFFIX = "_v3"


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vscale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def vlen(a):
    return math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)


def vnorm(a):
    l = vlen(a)
    return (a[0] / l, a[1] / l, a[2] / l)


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


class MeshBuilder:
    def __init__(self):
        self.positions = []
        self.normals = []
        self.tris = []  # indices into positions/normals (shared index)

    def add_vertex(self, p, n):
        self.positions.append(p)
        self.normals.append(n)
        return len(self.positions) - 1

    def add_tube(self, path, radius, cap_start=True, cap_end=True,
                 end_cut_normal=None, end_flare=1.0):
        """Sweeps a circle along a polyline, sharing rings at the joints.

        end_cut_normal: if set, the final ring is projected onto the plane
        through the last station with this normal — a mitre cut, like the
        angled opening of a classic 4x4 snorkel. end_flare scales the final
        ring radius slightly outward.
        """
        # ring orientation per station: average of adjacent segment tangents
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
            # build a frame perpendicular to the tangent
            ref = (1.0, 0.0, 0.0) if abs(t[0]) < 0.9 else (0.0, 1.0, 0.0)
            u = vnorm(vcross(t, ref))
            w = vnorm(vcross(t, u))
            ring = []
            for s in range(SEGMENTS):
                a = 2 * math.pi * s / SEGMENTS
                n = vadd(vscale(u, math.cos(a)), vscale(w, math.sin(a)))
                vtx = vadd(p, vscale(n, r))
                if is_last and end_cut_normal is not None:
                    # slide the vertex along the tube axis onto the cut plane
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


def build_snorkel(size):
    m = MeshBuilder()
    path = PATHS[size]
    # main tube with a flared, forward-facing mitre-cut opening at the top
    m.add_tube(path, TUBE_R, cap_start=True, cap_end=True,
               end_cut_normal=MITRE_N, end_flare=FLARE)
    # bracket stubs toward the cab (inboard, +x direction) along the pillar run
    pillar_a, pillar_b = path[2], path[-2]
    for frac in (0.3, 0.8):
        base = vadd(pillar_a, vscale(vsub(pillar_b, pillar_a), frac))
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


def main():
    sizes = ("small", "medium", "tall")
    geoms = []
    nodes = []
    for size in sizes:
        name = f"snorkel_{size}{OBJ_SUFFIX}"
        geoms.append(geometry_xml(name, build_snorkel(size)))
        nodes.append(node_xml(name))

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
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
    out = os.path.join(os.path.dirname(__file__), "..",
                       "vehicles", "pickup", "universalSnorkel", "snorkel.dae")
    out = os.path.normpath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(dae)
    print("wrote", out)
    for size in sizes:
        print(f"  snorkel_{size}{OBJ_SUFFIX}: opening at {PATHS[size][-1]}")


if __name__ == "__main__":
    main()
