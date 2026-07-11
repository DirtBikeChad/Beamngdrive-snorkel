#!/usr/bin/env python3
"""Generates the snorkel meshes (snorkel.dae) for the D-Series parts.

Produces one COLLADA file containing three objects (snorkel_small,
snorkel_medium, snorkel_tall), each a tube that runs from the engine bay,
over the right fender, up the A-pillar, ending in a forward-facing ram head.
Also adds two bracket stubs toward the cab.

Run from the repo root:  python3 tools/generate_snorkel_dae.py
Output: vehicles/pickup/universalSnorkel/snorkel.dae
"""

import math
import os

SEGMENTS = 20          # radial resolution of the tubes
TUBE_R = 0.042         # main tube radius (~84 mm OD, typical safari snorkel)
HEAD_R = 0.062         # ram head radius
HEAD_LEN = 0.17        # ram head length
BRACKET_R = 0.016
BRACKET_LEN = 0.085    # bracket stub toward the cab
MATERIAL = "snorkel_black"

# Path stations in vehicle space (x right(-)/left(+), y front(-)/rear(+), z up)
P0 = (-0.90, -1.16, 0.97)   # engine-bay end, above/behind right fender area
P1 = (-0.995, -0.86, 1.04)  # over the fender edge, start of the vertical run
P2 = (-0.995, -0.74, 1.08)  # A-pillar base
TIP_TALL = (-0.995, -0.40, 1.86)  # roof line
# A-pillar direction from P2 to TIP_TALL; small/medium tips lie along it
TIP_Z = {"small": 1.24, "medium": 1.54, "tall": 1.86}
HEAD_DIR = (0.0, -0.966, 0.259)   # ram head axis: forward, tilted 15 deg up


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


def tip_for(size):
    d = vnorm(vsub(TIP_TALL, P2))
    t = (TIP_Z[size] - P2[2]) / d[2]
    return vadd(P2, vscale(d, t))


class MeshBuilder:
    def __init__(self):
        self.positions = []
        self.normals = []
        self.tris = []  # indices into positions/normals (shared index)

    def add_vertex(self, p, n):
        self.positions.append(p)
        self.normals.append(n)
        return len(self.positions) - 1

    def add_tube(self, path, radius, cap_start=True, cap_end=True):
        """Sweeps a circle along a polyline, sharing rings at the joints."""
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
        for p, t in zip(path, tangents):
            # build a frame perpendicular to the tangent
            ref = (1.0, 0.0, 0.0) if abs(t[0]) < 0.9 else (0.0, 1.0, 0.0)
            u = vnorm(vcross(t, ref))
            w = vnorm(vcross(t, u))
            ring = []
            for s in range(SEGMENTS):
                a = 2 * math.pi * s / SEGMENTS
                n = vadd(vscale(u, math.cos(a)), vscale(w, math.sin(a)))
                ring.append(self.add_vertex(vadd(p, vscale(n, radius)), n))
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
    tip = tip_for(size)
    # main tube: engine bay -> fender -> A-pillar -> tip
    m.add_tube([P0, P1, P2, tip], TUBE_R, cap_start=True, cap_end=True)
    # ram head: wider tube from just behind the tip, facing forward/up
    head_start = vadd(tip, vscale(HEAD_DIR, -0.02))
    head_end = vadd(tip, vscale(HEAD_DIR, HEAD_LEN))
    m.add_tube([head_start, head_end], HEAD_R, cap_start=True, cap_end=True)
    # bracket stubs toward the cab (inboard, +x direction)
    for frac in (0.25, 0.75):
        base = vadd(P2, vscale(vsub(tip, P2), frac))
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
        name = f"snorkel_{size}"
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
        print(f"  snorkel_{size}: tip at {tip_for(size)}")


if __name__ == "__main__":
    main()
