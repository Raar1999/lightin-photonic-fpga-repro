"""
4x4 square recirculating mesh: 25 vertices, 40 edges, one PUC per edge.

The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was not
available, so results from this mesh are conditional on the wiring and are reported for
both WIRING_A and WIRING_B.

Geometry
--------
Vertices form a 5x5 lattice indexed (r, c), r and c in 0..4, r downward and c rightward.
Edges carry one PUC each:

    horizontal  H[r][c]  joins (r, c) -- (r, c+1)      r in 0..4, c in 0..3   -> 20 edges
    vertical    V[r][c]  joins (r, c) -- (r+1, c)      r in 0..3, c in 0..4   -> 20 edges

The PUC index order is fixed and die-independent: index 0..19 are the horizontal edges in
row-major order (r outer, c inner), and index 20..39 the vertical edges in row-major order.
`edge_of_index` and `index_of_edge` convert either way. The caller supplies a length-40
array of phases in that order.

A PUC's "L" end sits at the lower-indexed vertex of its edge and its "R" end at the higher:
for H[r][c] that is (r, c) and (r, c+1); for V[r][c] it is (r, c) and (r+1, c). Each end
carries two waveguides, wg 0 and wg 1.

Every inter-MZI waveguide is given the same length, `side_um`, which is the preprint's
statement that the waveguide lengths among the MZIs in the square mesh are designed equal
(arXiv:2504.01463v2 section 3). The grating-to-MZI sections, which the preprint says are
*not* equal and carry no phase shifter, are outside this model.

Vertex wiring
-------------
At a vertex, the incident edge-ends arrive from up to four directions: N, E, S, W. Each end
has two waveguides, so a degree-d vertex has 2d ports. `Circuit.connect` joins exactly two
ports, so the ends must be matched in pairs; when two ends are matched, their wg 0 ports are
joined and their wg 1 ports are joined. An end left over at a boundary vertex becomes two
external ports.

Both rules are greedy over a fixed preference list of direction pairs, and neither depends
on the die, the challenge or the wavelength.

WIRING_A -- straight where an opposite edge exists, otherwise a clockwise turn:

    preference   N-S, E-W,  then  N-E, E-S, S-W, W-N

    incident     outgoing (degree-4 vertex)   outgoing (degree-3 vertex, by missing side)
    N            S                            missing N: E->W, S external
    E            W                            missing E: N->S, W external
    S            N                            missing S: E->W, N external
    W            E                            missing W: N->S, E external

WIRING_B -- turn first, straight only when no turn is available:

    preference   N-E, E-S, S-W, W-N,  then  N-S, E-W

    incident     outgoing (degree-4 vertex)   outgoing (degree-3 vertex, by missing side)
    N            E                            missing N: E->S, W external
    E            N                            missing E: S->W, N external
    S            W                            missing S: N->E, W external
    W            S                            missing W: N->E, S external

External ports
--------------
The preprint's chip has 20 optical ports, ten on each of two opposite edges
(arXiv:2504.01463v2 section 4.1). This lattice cannot reproduce that split. Every edge-end
lies at a vertex, so an external port can only be an end the vertex pairing leaves over.
Corners have degree 2 and interior vertices degree 4, and both are matched exactly; only
the 12 degree-3 boundary vertices leave an end over, three per lattice side. Both wirings
therefore expose 12 unmatched ends, 24 external ports, six per side, rather than 20 ports
in a ten-and-ten split. All 24 are declared external: an undeclared boundary end would
drop its power out of the energy accounting rather than conserve it.

Rotational symmetry
-------------------
The 90-degree rotation (r, c) -> (c, 4-r) maps the lattice to itself and carries directions
N->E->S->W->N. It maps H[r][c] to V[c][4-r] and V[r][c] to H[c][3-r], so it permutes the 40
edges. WIRING_A commutes with it; WIRING_B does not, and cannot: at a degree-4 vertex the
only all-turn matchings are {N-E, S-W} and {E-S, W-N}, and the rotation swaps them, so no
turn-first rule is invariant under a quarter turn. `wiring_is_rotation_equivariant` checks
this directly. The PUF of `ppuf_recirc.py` relies on the symmetry and therefore defaults to
WIRING_A; WIRING_B is kept as the contrasting wiring the results are reported against.
"""

import numpy as np

from .puc import puc_matrix
from .recirculating import Circuit, unitarity_check   # noqa: F401  (re-exported for tests)

N_SIDE = 5                     # vertices per side of the lattice
N_CELLS = 4                    # square cells per side
SIDE_UM = 500.0                # inter-MZI waveguide length (paper Methods, square-mesh side)

DIRECTIONS = ("N", "E", "S", "W")
ROT_DIR = {"N": "E", "E": "S", "S": "W", "W": "N"}   # image of a direction under the rotation

WIRING_A = ("A", (("N", "S"), ("E", "W"),
                  ("N", "E"), ("E", "S"), ("S", "W"), ("W", "N")))
WIRING_B = ("B", (("N", "E"), ("E", "S"), ("S", "W"), ("W", "N"),
                  ("N", "S"), ("E", "W")))
WIRINGS = {"A": WIRING_A, "B": WIRING_B}


# --------------------------------------------------------------------------- indexing
def edge_of_index(k):
    """('H'|'V', r, c) for PUC index k, in the fixed order stated in the module docstring."""
    if not 0 <= k < 40:
        raise ValueError(f"PUC index must be in 0..39, got {k}")
    if k < 20:
        return ("H", k // N_CELLS, k % N_CELLS)
    k -= 20
    return ("V", k // N_SIDE, k % N_SIDE)


def index_of_edge(kind, r, c):
    """PUC index of edge H[r][c] or V[r][c]."""
    if kind == "H":
        if not (0 <= r < N_SIDE and 0 <= c < N_CELLS):
            raise ValueError(f"no horizontal edge H[{r}][{c}]")
        return r * N_CELLS + c
    if kind == "V":
        if not (0 <= r < N_CELLS and 0 <= c < N_SIDE):
            raise ValueError(f"no vertical edge V[{r}][{c}]")
        return 20 + r * N_SIDE + c
    raise ValueError(f"edge kind must be 'H' or 'V', got {kind!r}")


def incident_ends(r, c):
    """{direction: (puc_index, side)} for the edge-ends meeting at vertex (r, c)."""
    ends = {}
    if r > 0:
        ends["N"] = (index_of_edge("V", r - 1, c), "R")
    if c < N_CELLS:
        ends["E"] = (index_of_edge("H", r, c), "L")
    if r < N_CELLS:
        ends["S"] = (index_of_edge("V", r, c), "L")
    if c > 0:
        ends["W"] = (index_of_edge("H", r, c - 1), "R")
    return ends


def rotate_edge(k):
    """PUC index of the image of edge k under the quarter turn (r, c) -> (c, 4-r)."""
    kind, r, c = edge_of_index(k)
    if kind == "H":
        return index_of_edge("V", c, N_CELLS - r)
    return index_of_edge("H", c, N_CELLS - 1 - r)


def rotate_end(pid, side):
    """Image of one edge-end (puc index, side) under the quarter turn.

    A horizontal edge keeps its side, because H[r][c] maps to V[c][4-r] with the lower
    vertex going to the lower vertex. A vertical edge flips: V[r][c] maps to H[c][3-r],
    and its L end at (r, c) lands on that edge's R end.
    """
    kind, _, _ = edge_of_index(pid)
    if kind == "H":
        return rotate_edge(pid), side
    return rotate_edge(pid), ("R" if side == "L" else "L")


def rotate_port(port):
    """Image of a Circuit port tuple (puc, side, wg) under the quarter turn."""
    pid, side, wg = port
    rp, rs = rotate_end(pid, side)
    return (rp, rs, wg)


def half_turn_port(port):
    """Image of a Circuit port tuple under the half turn, i.e. the quarter turn twice."""
    return rotate_port(rotate_port(port))


def half_turn_edge(k):
    """PUC index of the image of edge k under the half turn (r, c) -> (4-r, 4-c)."""
    kind, r, c = edge_of_index(k)
    if kind == "H":
        return index_of_edge("H", N_CELLS - r, N_CELLS - 1 - c)
    return index_of_edge("V", N_CELLS - 1 - r, N_CELLS - c)


def half_turn_orbits():
    """The 40 PUC indices grouped into half-turn orbits, each sorted, in fixed order.

    The half turn fixes no edge, so every orbit has size 2 and there are 20 of them.
    """
    seen, orbits = set(), []
    for k in range(40):
        if k in seen:
            continue
        orb, j = [], k
        while j not in seen:
            seen.add(j)
            orb.append(j)
            j = half_turn_edge(j)
        orbits.append(sorted(orb))
    return sorted(orbits, key=lambda o: o[0])


def edge_orbits():
    """The 40 PUC indices grouped into orbits of the quarter turn, each orbit sorted.

    Returned in ascending order of each orbit's smallest index, so the grouping is fixed
    and die-independent.
    """
    seen, orbits = set(), []
    for k in range(40):
        if k in seen:
            continue
        orb, j = [], k
        while j not in seen:
            seen.add(j)
            orb.append(j)
            j = rotate_edge(j)
        orbits.append(sorted(orb))
    return sorted(orbits, key=lambda o: o[0])


# --------------------------------------------------------------------------- wiring
def vertex_pairing(r, c, wiring=WIRING_A):
    """(matched, leftover) for one vertex: a list of direction pairs and the spare ends.

    Greedy over the wiring's preference list; a direction pair is taken when both its
    directions are present at this vertex and neither has been matched already.
    """
    ends = incident_ends(r, c)
    used, matched = set(), []
    for a, b in wiring[1]:
        if a in ends and b in ends and a not in used and b not in used:
            matched.append((a, b))
            used.update((a, b))
    return matched, [d for d in DIRECTIONS if d in ends and d not in used]


def boundary_ends(wiring=WIRING_A):
    """[(r, c, direction, puc_index, side)] for every edge-end the wiring leaves unmatched."""
    out = []
    for r in range(N_SIDE):
        for c in range(N_SIDE):
            _, leftover = vertex_pairing(r, c, wiring)
            for d in leftover:
                pid, side = incident_ends(r, c)[d]
                out.append((r, c, d, pid, side))
    return out


def boundary_ports(wiring=WIRING_A):
    """Every external port, as Circuit port tuples, in the fixed boundary-end order."""
    return [(pid, side, wg) for (_, _, _, pid, side) in boundary_ends(wiring)
            for wg in (0, 1)]


def wiring_is_rotation_equivariant(wiring):
    """True when the wiring's vertex pairing commutes with the quarter turn everywhere.

    The PUF design depends on this: if it is false, two output ports that the rotation
    maps to one another are not fed by mirror-image paths and their powers differ even
    in a die with no fabrication error.
    """
    for r in range(N_SIDE):
        for c in range(N_SIDE):
            matched, _ = vertex_pairing(r, c, wiring)
            rr, rc = c, N_CELLS - r
            rot_matched, _ = vertex_pairing(rr, rc, wiring)
            want = {frozenset((ROT_DIR[a], ROT_DIR[b])) for a, b in matched}
            got = {frozenset(p) for p in rot_matched}
            if want != got:
                return False
    return True


# ------------------------------------------------------------------- port-level rules
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}   # half-turn action on directions


def slots():
    """The eight (direction, waveguide) slots an interior vertex carries."""
    return [(d, w) for d in DIRECTIONS for w in (0, 1)]


def half_turn_slot(slot):
    """Image of a (direction, waveguide) slot under the half turn (r,c) -> (4-r, 4-c)."""
    d, w = slot
    return (OPP[d], w)


def perfect_matchings(items):
    """Every perfect matching of an even-length list, as lists of pairs."""
    if not items:
        yield []
        return
    a, rest0 = items[0], items[1:]
    for i, b in enumerate(rest0):
        rest = rest0[:i] + rest0[i + 1:]
        for m in perfect_matchings(rest):
            yield [(a, b)] + m


def rule_from_matching(matching):
    """{slot: partner slot} involution from a list of slot pairs."""
    rule = {}
    for a, b in matching:
        rule[a] = b
        rule[b] = a
    return rule


def rule_is_half_turn_invariant(rule):
    """True when the matching is unchanged by the half-turn relabelling of directions."""
    pairs = {frozenset((a, b)) for a, b in rule.items()}
    img = {frozenset((half_turn_slot(a), half_turn_slot(b))) for a, b in rule.items()}
    return pairs == img


def build_port_mesh(thetas, rule, side_um=SIDE_UM, n_eff=2.36, loss_db_cm=2.0,
                    inputs=None, outputs=None, extra_io=None):
    """The 40-cell mesh wired by a port-level rule rather than a direction preference.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.

    `rule` maps each (direction, waveguide) slot to the slot it is joined to at every
    vertex; a slot whose partner's direction is absent at a given vertex leaves that port
    unconnected, and it becomes external. `extra_io` is an optional list of
    (port, length_um) grating waveguides; each named port is then reached only through its
    own waveguide and the far end is the external port.
    """
    thetas = np.asarray(thetas, dtype=float)
    if thetas.shape != (40,):
        raise ValueError(f"expected 40 phases, got shape {thetas.shape}")
    c = Circuit(n_eff=n_eff, loss_db_cm=loss_db_cm)
    for k in range(40):
        c.add_puc(k, puc_matrix(thetas[k]))
    for r in range(N_SIDE):
        for cc in range(N_SIDE):
            ends = incident_ends(r, cc)
            done = set()
            for slot in slots():
                if slot in done:
                    continue
                partner = rule[slot]
                d, w = slot
                d2, w2 = partner
                if d not in ends or d2 not in ends:
                    continue
                pid, side = ends[d]
                pid2, side2 = ends[d2]
                pa, pb = (pid, side, w), (pid2, side2, w2)
                done.update((slot, partner))
                if pa == pb:
                    continue
                c.connect(pa, pb, side_um)
    ports = unconnected_ports(c)
    c.set_io(inputs=list(ports) if inputs is None else list(inputs),
             outputs=list(ports) if outputs is None else list(outputs))
    return c


def unconnected_ports(circuit):
    """Every port of a built circuit that no connection touches, in port order."""
    used = set()
    for (a, b, _length) in circuit.connections:
        used.update((a, b))
    return [p for p in circuit.ports if p not in used]


def boundary_ports_for_rule(rule):
    """External ports a port-level rule leaves, without solving anything."""
    return unconnected_ports(build_port_mesh(np.zeros(40), rule))


# ------------------------------------------------------- boundary grating waveguides
N_OPTICAL_PORTS = 20        # preprint section 4.1: 20 gratings, ten per opposite edge
GRATING_WG_UM = 250.0       # stated length of one grating-to-MZI waveguide
GRATING_SPACING_UM = 222.22  # preprint section 4.1, recorded; not used by the solver


def vertex_of_port(port):
    """The lattice vertex (r, c) a port sits at."""
    pid, side, _wg = port
    kind, r, c = edge_of_index(pid)
    if kind == "H":
        return (r, c) if side == "L" else (r, c + 1)
    return (r, c) if side == "L" else (r + 1, c)


def grating_ports(rule, n_ports=N_OPTICAL_PORTS):
    """The boundary ends that carry a grating waveguide: half on top, half on the bottom.

    The preprint fixes the count and the placement -- 20 ports, ten on each of two
    opposite edges (section 4.1). Which boundary end each one attaches to is a stated
    choice: the first n/2 unconnected ports at a top-edge vertex, in the fixed port order
    of this module, and their half-turn images on the bottom edge. Choosing the bottom set
    as the image of the top set is what makes the whole 20 map onto itself under the half
    turn, which the PUF design needs.
    """
    free = unconnected_ports(build_port_mesh(np.zeros(40), rule))
    top = [p for p in free if vertex_of_port(p)[0] == 0]
    if len(top) < n_ports // 2:
        raise ValueError(f"only {len(top)} free top-edge ports, need {n_ports // 2}")
    chosen_top = top[:n_ports // 2]
    chosen_bottom = [half_turn_port(p) for p in chosen_top]
    missing = [p for p in chosen_bottom if p not in set(free)]
    if missing:
        raise ValueError(f"half-turn images not free boundary ends: {missing}")
    return chosen_top + chosen_bottom


def grating_amplitude(lam_nm, length_um=GRATING_WG_UM, n_eff=2.36, loss_db_cm=2.0):
    """Complex transmission of one grating-to-MZI waveguide.

    Every port is given the same length, which keeps the half-turn symmetry exact. The
    preprint says the real sections are *not* uniform and carry no phase shifter
    (section 3); that non-uniformity is not modelled here. Under equal lengths this factor
    is common to all 20 ports, so it cancels out of every response-bit comparison and out
    of the relative phase of the two injected beams: it is carried for completeness rather
    than because it changes a result.
    """
    L_m = length_um * 1e-6
    phase = 2 * np.pi * n_eff * L_m / (lam_nm * 1e-9)
    amp = 10 ** (-(loss_db_cm * (length_um * 1e-4)) / 20.0)
    return amp * np.exp(-1j * phase)


def free_top_ends(rule):
    """Unconnected boundary ports at a top-edge vertex, in fixed port order."""
    free = unconnected_ports(build_port_mesh(np.zeros(40), rule))
    return [p for p in free if vertex_of_port(p)[0] == 0]


def io_mesh_from_ports(thetas, rule, ports, side_um=SIDE_UM, n_eff=2.36,
                       loss_db_cm=2.0, inputs=None):
    """`build_io_mesh` with the 20 optical ports supplied rather than chosen here."""
    mesh = build_port_mesh(thetas, rule, side_um=side_um, n_eff=n_eff,
                           loss_db_cm=loss_db_cm,
                           inputs=list(ports) if inputs is None else list(inputs),
                           outputs=list(ports))
    mesh.optical_ports = list(ports)
    mesh.terminated_ports = [p for p in unconnected_ports(mesh) if p not in set(ports)]
    return mesh


def build_io_mesh(thetas, rule, n_ports=N_OPTICAL_PORTS, side_um=SIDE_UM,
                  n_eff=2.36, loss_db_cm=2.0, inputs=None):
    """The 40-cell mesh with exactly `n_ports` external optical ports.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring.

    Boundary ends that do not carry a grating waveguide are left terminated: they are not
    declared external, so their power leaves the accounting the way an unused, absorbed
    waveguide end does on a chip. `energy_audit` adds the two halves back up.
    """
    gp = grating_ports(rule, n_ports)
    mesh = build_port_mesh(thetas, rule, side_um=side_um, n_eff=n_eff,
                           loss_db_cm=loss_db_cm,
                           inputs=list(gp) if inputs is None else list(inputs),
                           outputs=list(gp))
    mesh.optical_ports = list(gp)
    mesh.terminated_ports = [p for p in unconnected_ports(mesh) if p not in set(gp)]
    return mesh


def energy_audit(mesh, lam_nm, injection, lossless=True):
    """(power out of the optical ports, power into terminated ends, their total).

    For a lossless build the total must be 1 per unit injected: it is the check that the
    vertex wiring neither loses nor creates power once the terminated ends are counted.
    """
    o = mesh.solve(lam_nm, injection, lossless=lossless)
    p_opt = sum(abs(o[mesh.pidx[p]]) ** 2 for p in mesh.optical_ports)
    p_term = sum(abs(o[mesh.pidx[p]]) ** 2 for p in mesh.terminated_ports)
    return float(p_opt), float(p_term), float(p_opt + p_term)


# --------------------------------------------------------------------------- build
def build_mesh(thetas, wiring=WIRING_A, side_um=SIDE_UM, n_eff=2.36, loss_db_cm=2.0,
               inputs=None, outputs=None):
    """The 40-cell mesh as a solvable Circuit, with one caller-supplied phase per PUC.

    The vertex wiring is a stated choice, not the paper's. The paper's Fig. 1 layout was
    not available, so results from this mesh are conditional on the wiring and are
    reported for both WIRING_A and WIRING_B.

    thetas is length 40 in the PUC index order of the module docstring. inputs and outputs
    default to every external port, which is what makes the lossless mesh conserve energy:
    leaving a boundary end undeclared would let its power vanish from the accounting.
    """
    thetas = np.asarray(thetas, dtype=float)
    if thetas.shape != (40,):
        raise ValueError(f"expected 40 phases, got shape {thetas.shape}")
    c = Circuit(n_eff=n_eff, loss_db_cm=loss_db_cm)
    for k in range(40):
        c.add_puc(k, puc_matrix(thetas[k]))
    for r in range(N_SIDE):
        for cc in range(N_SIDE):
            ends = incident_ends(r, cc)
            matched, _ = vertex_pairing(r, cc, wiring)
            for a, b in matched:
                (pa, sa), (pb, sb) = ends[a], ends[b]
                for wg in (0, 1):
                    c.connect((pa, sa, wg), (pb, sb, wg), side_um)
    ports = boundary_ports(wiring)
    c.set_io(inputs=list(ports) if inputs is None else list(inputs),
             outputs=list(ports) if outputs is None else list(outputs))
    return c
