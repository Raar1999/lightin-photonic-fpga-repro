"""
Search the vertex wirings of the 4x4 square mesh instead of hand-picking one.

The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was not
available, so results from this mesh are conditional on the wiring and are reported for
both selected wirings.

What is enumerated
------------------
An interior vertex of the 5x5 lattice carries **eight** ports, not four: each of the four
incident PUC ends has two waveguides (`puc_4port` gives every PUC the ports L0, L1, R0, R1).
A vertex wiring is therefore a perfect matching of eight labelled ports, of which there are
7!! = 105; a degree-3 boundary vertex has six ports and 5!! = 15 matchings.

A wiring here is one matching of the eight (direction, waveguide) slots, applied at every
vertex, with a pair dropped wherever one of its two directions is absent -- which is what
leaves a port unconnected and so external. That keeps the rule uniform, die-independent and
wavelength-independent, and makes the global wiring half-turn invariant exactly when the
slot matching is.

Which rotation
--------------
The preprint puts 20 optical ports on two opposite edges of the chip. A quarter turn of the
lattice carries {top, bottom} to {left, right}, so it maps the port-bearing edges onto the
two edges that carry none and cannot preserve the stated port set; a half turn carries top
to bottom and bottom to top and does preserve it. The search therefore keeps half-turn
invariance, which is the strongest rotational symmetry the stated port layout admits.

Scope of the enumeration
------------------------
This is exhaustive over *uniform* rules: all 105 slot matchings are generated and the 25
half-turn-invariant ones kept. It is **not** exhaustive over all possible global wirings,
because a real layout may use different matchings at different vertices; that space is
105 raised to the number of half-turn orbits of vertices and is not enumerated here. No
claim in this module is a theorem about every wiring of the lattice.

Selection
---------
Surviving wirings are ranked by, in order: all 40 cells reachable from one injection port;
both injection beams able to interfere; 20 external ports split evenly over two opposite
edges; then the largest number of live response pairs. `search_report()` returns the full
table and `rejected_alternatives()` the ones that lost.

Of the 25, twelve reach all 40 cells with both beams interfering. None produces 20 external
ports on two opposite edges -- the twelve connected ones leave 32 or 36 unconnected ports,
spread over all four edges and the corners -- so the third criterion selects nothing and the
ranking falls through to the live-pair count. Step D adds the preprint's dedicated grating
waveguides, which is what fixes the port count and placement.

The two selected are:

    WIRING_C4_FREE_1   N0-E1 N1-S1 E0-W0 S0-W1    40 cells, interfering, 36 ext, 11/17 live
    WIRING_C4_FREE_2   N0-S0 N1-E1 E0-W0 S1-W1    40 cells, interfering, 36 ext, 11/17 live

Rejected, by the criterion that lost:

  * nine more reach all 40 cells and interfere but light fewer response pairs
    (9/17, then 3/17, then 2/15);
  * four reach only 8 or 4 cells with the beams unable to meet, among them
    `N0-S0 N1-S1 E0-W0 E1-W1`, the straight-through rule used before this search, which
    reaches 4 of 40 cells;
  * four produce exactly 20 external ports but reach only 4 cells;
  * `N0-N1 E0-E1 S0-S1 W0-W1` reflects every port straight back and produces no external
    port at all.

The names record that these are free of the quarter-turn (C4) constraint, which the port
layout rules out in any case.
"""

import numpy as np

from . import square_mesh as SM


def _vertex_of_port(port):
    """The lattice vertex (r, c) a port sits at."""
    pid, side, _wg = port
    kind, r, c = SM.edge_of_index(pid)
    if kind == "H":
        return (r, c) if side == "L" else (r, c + 1)
    return (r, c) if side == "L" else (r + 1, c)


def _edge_label(vertex):
    r, c = vertex
    lab = []
    if r == 0:
        lab.append("top")
    if r == SM.N_CELLS:
        lab.append("bottom")
    if c == 0:
        lab.append("left")
    if c == SM.N_CELLS:
        lab.append("right")
    return "+".join(lab) if lab else "interior"


def invariant_rules():
    """The half-turn-invariant slot matchings, as {slot: partner} dicts."""
    out = []
    for m in SM.perfect_matchings(SM.slots()):
        rule = SM.rule_from_matching(m)
        if SM.rule_is_half_turn_invariant(rule):
            out.append(rule)
    return out


def _adjacency(mesh):
    """Port adjacency: the wiring connections plus each PUC's own four ports."""
    adj = {}
    for (a, b, _length) in mesh.connections:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    for k in range(40):
        ps = [(k, sd, wg) for sd in ("L", "R") for wg in (0, 1)]
        for q in ps:
            adj.setdefault(q, []).extend(x for x in ps if x != q)
    return adj


def _reachable(mesh, start):
    adj = _adjacency(mesh)
    seen, stack = {start}, [start]
    while stack:
        q = stack.pop()
        for x in adj.get(q, []):
            if x not in seen:
                seen.add(x)
                stack.append(x)
    return seen


def half_turn_pairs(ports):
    """External ports grouped into half-turn pairs, in fixed order; unpaired ones dropped."""
    pset, pairs, used = set(ports), [], set()
    for p in ports:
        if p in used:
            continue
        q = SM.half_turn_port(p)
        if q in pset and q != p and q not in used:
            used.update((p, q))
            pairs.append((p, q))
    return pairs


def evaluate_rule(rule, lam_nm=1560.0, seed=0):
    """The five quantities of the search for one wiring.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.
    """
    mesh0 = SM.build_port_mesh(np.zeros(40), rule)
    ports = SM.unconnected_ports(mesh0)
    info = {
        "n_external": len(ports),
        "edges": {},
        "n_cells_reachable": 0,
        "beams_interfere": False,
        "unitarity_dev": float("nan"),
        "live_pairs": 0,
        "n_pairs": 0,
    }
    for p in ports:
        lab = _edge_label(_vertex_of_port(p))
        info["edges"][lab] = info["edges"].get(lab, 0) + 1
    pairs = half_turn_pairs(ports)
    info["n_pairs"] = max(0, len(pairs) - 1)
    if not pairs:
        return info

    inj = list(pairs[0])
    reach = _reachable(mesh0, inj[0])
    info["n_cells_reachable"] = len({q[0] for q in reach})
    info["beams_interfere"] = inj[1] in reach

    lossless = SM.build_port_mesh(np.zeros(40), rule, loss_db_cm=0.0,
                                  inputs=inj, outputs=ports)
    info["unitarity_dev"] = SM.unitarity_check(lossless, lam_nm)

    rng = np.random.default_rng(seed)
    theta = rng.normal(0.0, 0.05, size=40)
    mesh = SM.build_port_mesh(theta, rule, inputs=inj, outputs=ports)
    o = mesh.solve(lam_nm, {p: 1 / np.sqrt(2) for p in inj})
    I = {p: float(np.abs(o[mesh.pidx[p]]) ** 2) for p in ports}
    info["live_pairs"] = sum(1 for a, b in pairs[1:]
                             if I[a] > 1e-12 and I[b] > 1e-12)
    return info


def _rank_key(info):
    """Selection order: all cells, then interference, then the 20/two-edge split, then live pairs."""
    edges = info["edges"]
    two_opposite = (edges.get("top", 0) == 10 and edges.get("bottom", 0) == 10) or \
                   (edges.get("left", 0) == 10 and edges.get("right", 0) == 10)
    return (info["n_cells_reachable"] == 40,
            info["beams_interfere"],
            info["n_external"] == 20 and two_opposite,
            info["live_pairs"],
            info["n_cells_reachable"])


def search_report():
    """[(index, rule, info)] for every surviving wiring, best first."""
    rows = [(i, r, evaluate_rule(r)) for i, r in enumerate(invariant_rules())]
    rows.sort(key=lambda t: _rank_key(t[2]), reverse=True)
    return rows


def _fmt_rule(rule):
    seen, out = set(), []
    for a in SM.slots():
        b = rule[a]
        if a in seen:
            continue
        seen.update((a, b))
        out.append(f"{a[0]}{a[1]}-{b[0]}{b[1]}")
    return " ".join(out)


_REPORT = None


def _report():
    global _REPORT
    if _REPORT is None:
        _REPORT = search_report()
    return _REPORT


def selected():
    """The two best wirings by the stated order, as (name, rule) pairs."""
    rows = _report()
    return [("C4_FREE_1", rows[0][1]), ("C4_FREE_2", rows[1][1])]


def rejected_alternatives():
    """[(index, rule_text, info)] for every surviving wiring that was not selected."""
    return [(i, _fmt_rule(r), info) for (i, r, info) in _report()[2:]]


def print_table():
    rows = _report()
    print(f"{'#':>3}  {'rule (slot pairs)':<40} {'cells':>5} {'interf':>6} "
          f"{'ext':>4} {'edge split':<28} {'unitarity':>10} {'live':>5}")
    for i, rule, info in rows:
        e = info["edges"]
        split = ",".join(f"{k}:{v}" for k, v in sorted(e.items()))
        print(f"{i:>3}  {_fmt_rule(rule):<40} {info['n_cells_reachable']:>5} "
              f"{str(info['beams_interfere']):>6} {info['n_external']:>4} "
              f"{split:<28} {info['unitarity_dev']:>10.1e} "
              f"{info['live_pairs']:>3}/{info['n_pairs']:<2}")
    return rows


def _selected_rules():
    return [r for _name, r in selected()]


WIRING_C4_FREE_1 = None   # set on first use by `selected()`; see `load_selected()`
WIRING_C4_FREE_2 = None


def load_selected():
    """Populate and return (WIRING_C4_FREE_1, WIRING_C4_FREE_2).

    The search runs 25 meshes, so it is done once on demand rather than at import.
    """
    global WIRING_C4_FREE_1, WIRING_C4_FREE_2
    if WIRING_C4_FREE_1 is None:
        WIRING_C4_FREE_1, WIRING_C4_FREE_2 = _selected_rules()
    return WIRING_C4_FREE_1, WIRING_C4_FREE_2


if __name__ == "__main__":
    print_table()
