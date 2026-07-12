#!/usr/bin/env python3
"""Validates every generated snorkel part against the rules that have bitten
us in the field:

  * jbeam parses (after stripping comments/trailing commas) and every beam
    references an existing node (own or engine e-node);
  * every flexbody mesh name exists in the vehicle's .dae;
  * no vertical node gap above MAX_GAP on the tube (flexbody shear rule);
  * worst per-node stiffness stays a healthy margin below the 2 kHz solver
    limit (spawn-explosion rule).

Run from the repo root: python3 tools/validate_mod.py
Exits non-zero on any violation.
"""

import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

MAX_GAP = 0.75          # metres; proven fine at 0.75, shears somewhere >0.8
STIFFNESS_MARGIN = 4    # worst node stiffness must stay below limit/margin
NODE_WEIGHT = 1.2
PHYS_RATE = 2000.0

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def parse_jbeam(path):
    raw = open(path).read()
    s = re.sub(r"//[^\n]*", "", raw)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return json.loads(s)


def dae_mesh_names(path):
    ns = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
    tree = ET.parse(path)
    return {g.get("name") for g in tree.findall(".//c:geometry", ns)}


def main():
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    jbeams = sorted(glob.glob(os.path.join(root, "vehicles", "*", "*", "*.jbeam")))
    check(len(jbeams) > 0, "no jbeam files found")
    limit = NODE_WEIGHT * (2 * PHYS_RATE) ** 2

    for jb in jbeams:
        veh_dir = os.path.dirname(jb)
        rel = os.path.relpath(jb, root)
        try:
            data = parse_jbeam(jb)
        except Exception as e:
            check(False, f"{rel}: jbeam does not parse: {e}")
            continue

        daes = glob.glob(os.path.join(veh_dir, "*.dae"))
        mesh_names = set()
        for d in daes:
            mesh_names |= dae_mesh_names(d)

        for part, body in data.items():
            for row in body.get("flexbodies", []):
                if isinstance(row, list) and row[0] != "mesh":
                    check(row[0] in mesh_names,
                          f"{rel}: {part}: flexbody mesh '{row[0]}' not in {daes}")
            if "nodes" not in body:
                continue
            nodes = [(r[0], r[3]) for r in body["nodes"]
                     if isinstance(r, list) and r[0] != "id"]
            own = {n for n, _ in nodes}
            beams = [(r[0], r[1]) for r in body["beams"]
                     if isinstance(r, list) and r[0] != "id1:"]
            for a, b in beams:
                check(a != b, f"{rel}: {part}: self-beam {a}")
                for n in (a, b):
                    check(n in own or n.startswith("e"),
                          f"{rel}: {part}: beam references unknown node '{n}'")
            seen = set()
            for b in map(frozenset, beams):
                check(b not in seen, f"{rel}: {part}: duplicate beam {sorted(b)}")
                seen.add(b)

            zs = sorted(z for n, z in nodes if n != "snb")
            gaps = [round(b - a, 3) for a, b in zip(zs, zs[1:])]
            check(max(gaps) <= MAX_GAP,
                  f"{rel}: {part}: node gap {max(gaps)} m exceeds {MAX_GAP} m")

            cur, load = 0, {}
            for r in body["beams"]:
                if isinstance(r, dict) and "beamSpring" in r:
                    cur = r["beamSpring"]
                if isinstance(r, list) and r[0] != "id1:":
                    for n in (r[0], r[1]):
                        if n in own:
                            load[n] = load.get(n, 0) + cur
            worst = max(load.values())
            check(worst < limit / STIFFNESS_MARGIN,
                  f"{rel}: {part}: worst node stiffness {worst/1e6:.1f}M vs limit {limit/1e6:.0f}M")

    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print(f"OK: {len(jbeams)} jbeam files validated, all rules pass")


if __name__ == "__main__":
    main()
