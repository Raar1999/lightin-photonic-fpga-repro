"""
Verification tests for the LightIN reproduction.
Run directly:  PYTHONPATH=. python3 tests/test_reproduction.py
Or with pytest: PYTHONPATH=. pytest -q
"""

import numpy as np
import pytest
from lightin import (puc, metrics, unitary, nonunitary, nn_iris, ppuf, mrm, switching,
                     throughput, coupler)


def test_puc_unitary():
    for th in np.linspace(0, 2 * np.pi, 9):
        T = puc.puc_matrix(th)
        assert np.max(np.abs(T.conj().T @ T - np.eye(2))) < 1e-12


def test_enob_matches_paper():
    assert abs(metrics.enob(0.0269) - 6.22) < 0.01      # paper 6.22 bit
    assert abs(metrics.enob(0.0453) - 5.47) < 0.01      # paper 5.47 bit


def test_latency_60ps():
    assert abs(metrics.propagation_latency(4.5e-3) * 1e12 - 60.0) < 0.5


def test_unitary_fidelity():
    U = unitary.random_unitary(4, seed=5)
    _, _, fid = unitary.fit_unitary(U, seed=5)
    assert fid > 0.999


def test_unitary_perm_routing_fidelity():
    u = unitary.run(verbose=False)
    assert u["perm_1"]["routing_fidelity"] >= 0.999
    assert u["perm_2"]["routing_fidelity"] >= 0.999


def test_nonunitary_modulus():
    info = nonunitary.run(verbose=False)
    assert info["modulus_corr"] > 0.999
    assert info["max_abs_err"] < 1e-9


def test_iris_accuracy():
    # five restarts rather than the reported fifteen: the best restart is kept, so this
    # is a lower bound on the reported accuracy and the threshold still discriminates
    res = nn_iris.train(restarts=5, seed=0)
    assert res["full_acc"] > 0.90                       # paper offline 94.67%


def test_ppuf_metrics():
    res = ppuf.evaluate(n_dies=40, n_challenges=64, seed=1)
    assert res["reliability_intra_die_HD"] < 0.05


def test_ppuf_responds_to_manufacturing_spread():
    """With negligible manufacturing spread, the response bits are set by measurement
    noise rather than by the die, so re-measurements of one die differ about as much as
    different dies do. With the paper's spread, the dies differ from each other far more
    than repeated measurements of one die."""
    lo, hi = ppuf.sensitivity_sweep(sigmas=(0.001, 1.05), n_dies=20, n_challenges=32)
    assert 0.40 <= hi["uniqueness"] <= 0.60
    assert 0.40 <= hi["uniformity"] <= 0.60
    assert hi["reliability"] < 0.10
    assert hi["tie_fraction"] < 0.05
    assert lo["reliability"] >= 0.5 * lo["uniqueness"]


def test_energy_exact():
    te = throughput.reproduce(verbose=False)
    assert abs(te["energy_pj_per_mac"] - 1.875) < 1e-6  # paper 1.875 pJ/MAC
    assert abs(te["tops"] - 1.92) < 1e-6


def test_switching_crosstalk_in_band():
    # the full C-band the paper claims, not a 10 nm window around the coupler's best point
    s = switching.crosstalk_summary(lambdas=np.linspace(1530, 1565, 141))
    assert s["cross"]["worst_xtalk_over_cband_db"] < -11.5


def test_cell_variant_matches_shipped_mzi():
    # the leakage diagnostic re-implements one cell; under its defaults it must be the
    # model, or the three cases it compares are not comparisons of this model
    ka, kb, ae = switching._cell_draws()
    for theta in (switching.THETA_BAR, switching.THETA_CROSS):
        ref = coupler.mzi_single_theta(theta, 1560.0, kappa0=ka[0], kappa0_b=kb[0],
                                       arm_phase_err=ae[0], excess_loss_db=0.1)
        got = switching._cell_variant(theta, 1560.0, ka[0], kb[0], ae[0])
        assert np.allclose(ref, got, atol=1e-15)


def test_arm_losses_are_equal_so_cannot_leak():
    # case (b) of the leakage diagnostic is a no-op by construction; if a per-arm loss
    # is ever added to the model this test fails and the attribution must be redone
    assert switching.ARM_LOSS_DB[0] == switching.ARM_LOSS_DB[1]
    lk = switching.leak_mechanism_check()
    for state in ("bar", "cross"):
        assert (lk[f"{state}_cell_leak_db_model"]
                == lk[f"{state}_cell_leak_db_equal_arm_loss"])


def test_bar_leak_needs_both_fabrication_terms():
    # with identical couplers and no arm phase error the bar state nulls exactly,
    # which is what makes the modelled bar crosstalk a statement about assumed spreads
    ka, kb, ae = switching._cell_draws()
    kmean = 0.5 * (ka[0] + kb[0])
    M = switching._cell_variant(switching.THETA_BAR, 1560.0, kmean, kmean, 0.0)
    assert abs(M[1, 0]) ** 2 < switching.ZERO_TOL


def test_mrm_lock_high_er():
    sw = mrm.run(verbose=False)
    assert sw["er_db"].max() > 12.0
    # monitoring peak is near the max-ER lock bias
    peak_bias = sw["bias"][np.argmax(sw["monitoring"])]
    assert abs(peak_bias - sw["lock_bias"]) < 0.1


def test_coupler_3db_at_fitted_wavelength():
    from lightin import coupler
    lam0 = coupler.DC_LAMBDA_3DB                                    # fitted, not 1560 nm
    assert abs(coupler.dc_power_coupling(lam0) - 0.5) < 1e-6        # 50:50 at lam0
    # an ideal 3-dB coupler nulls exactly, so the extinction is unbounded, not a number
    assert coupler.extinction_ratio_db(lam0) is None
    assert coupler.extinction_ratio_db(1520.0) < 30.0


def test_nominal_split_is_the_three_db_point():
    """The nominal coupler split is not a free choice: it is what "3 dB" means.

    §6.3 records the 3-dB definition as the source of `DC_KAPPA0_NOMINAL`, which is the
    only one of the parameters §6.3 had recorded as unsourced that turned out to have one.
    This test is
    what makes that record falsifiable: 0.5 is half the power, and `DC_LAMBDA_3DB` is
    named for the wavelength where this coupler reaches it. Change the split away from 0.5
    and the source stops being true, whatever the table still says.

    `test_coupler_3db_at_fitted_wavelength` above checks the fit against the literal 0.5
    and so would not notice the constant moving; this checks the constant itself.
    """
    from lightin import coupler, switching
    assert 10 * np.log10(coupler.DC_KAPPA0_NOMINAL) == pytest.approx(-3.0, abs=0.02)
    # switching draws its nominal split from the same constant, so the two cannot diverge
    assert switching.DC_KAPPA0_NOMINAL == coupler.DC_KAPPA0_NOMINAL


def test_coupler_dispersion_fit():
    from lightin import coupler
    lam, k = coupler._demo_measured_dataset(seed=3)
    k0, slope, rms = coupler.fit_dc_dispersion(lam, k, lam0=coupler.DEMO_LAMBDA0)
    assert abs(k0 - 0.5) < 0.05 and rms < 0.01                     # recovers parameters


def test_demo_fit_recovers_generator_parameters():
    """The fitted demo coupler parameters must match the ones the generator used.

    Generator and fitter reference kappa0 to the same wavelength (DC_LAMBDA_3DB), so a
    disagreement here is a real fit failure and not a change of reference wavelength.
    Tolerances: 0.01 absolute on kappa0 (the data carry 0.004 noise on 25 points) and
    10% relative on slope (the generator's quadratic term is outside the fit form).
    """
    from lightin import coupler
    out = coupler.run(verbose=False)
    demo_fit_kappa0, demo_true_kappa0 = out["fit_kappa0"], out["demo_true_kappa0"]
    demo_fit_slope, demo_true_slope = out["fit_slope"], out["demo_true_slope"]
    assert abs(demo_fit_kappa0 - demo_true_kappa0) < 0.01
    assert abs(demo_fit_slope - demo_true_slope) / demo_true_slope < 0.10


def test_expressivity_ladder():
    from lightin import expressivity
    dof = expressivity.dof_counts(4)
    assert dof["single_theta"] == 6 and dof["two_dof_universal"] == 16
    gap = expressivity.haar_fidelity_gap(n_samples=4, seed=2)
    assert gap["single_theta"].mean() < 0.85                       # limited expressivity
    assert gap["two_dof_universal"].mean() > 0.999                 # universal


def test_expressivity_permutation_routing():
    from lightin import expressivity
    perms = expressivity.permutation_reachability()
    assert perms["perm_1"]["routing_single_theta"] > 0.99          # routing reachable
    assert perms["perm_1"]["gate_fidelity_with_output_phases"] > 0.99


def test_recirc_ring_matches_analytic():
    from lightin import recirculating
    _, _, _, rms = recirculating.validate_ring(verbose=False)
    assert rms < 1e-9                                              # SMN == analytic ring


def test_recirc_add_drop_matches_analytic():
    from lightin import recirculating
    _, _, _, rms = recirculating.validate_add_drop(verbose=False)
    assert rms < 1e-9


def test_recirc_square_plaquette_unitary():
    from lightin import recirculating
    import numpy as _np
    plaq = recirculating.square_plaquette(_np.array([0.3, 1.1, 2.0, 2.7]))
    assert recirculating.unitarity_check(plaq, 1550.3) < 1e-9      # energy conserved (wiring OK)


def test_recirc_scales_to_40_pucs():
    from lightin import recirculating
    big = recirculating.multi_ring_bus(40)
    assert len(big.Sc) == 40
    assert recirculating.unitarity_check(big, 1550.37) < 1e-9


def test_recirc_feedback_creates_resonance():
    from lightin import recirculating
    _, p_ff, p_ring = recirculating.fir_vs_iir(verbose=False)
    # feedforward MZI is flat (FIR); ring has deep resonances (IIR)
    assert (p_ff.max() - p_ff.min()) < 1e-3
    assert (p_ring.max() - p_ring.min()) > 0.3




def test_fig4d_digitized_fit():
    """Both Fig 4d models fit the digitized points, and the mesh fit is what ships.

    Only the two single fits are run: the bootstraps in fit_fig4.main() cost minutes
    and answer a different question (how wide the interval is), which the report takes
    from results.json rather than from the suite. 2.0 dB is the digitization
    uncertainty the CSV header states.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4
    from lightin.coupler import DC_LAMBDA_3DB, DC_SLOPE
    proxy = fit_fig4.fit_proxy()
    mesh = fit_fig4.fit_mesh()
    assert proxy["rms_db"] <= 2.0
    assert mesh["rms_db"] <= 2.0
    # the shipped constants are the mesh fit rounded, so they must still match it
    assert abs(mesh["lambda0"] - DC_LAMBDA_3DB) <= 0.1
    assert abs(mesh["slope"] - DC_SLOPE) / DC_SLOPE <= 0.05


def test_mesh_model_matches_fig4d():
    """The mesh T20 model at the shipped constants must track the digitized Fig 4d curve.

    DC_LAMBDA_3DB, DC_SLOPE and FIG4D_FLOOR_DB are the mesh fit rounded for the source,
    so this checks both the fit and the rounding. 2.0 dB is the digitization uncertainty
    the CSV header states; a larger RMS would mean the shipped coupler no longer
    describes the curve it was fitted to.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4
    from lightin import coupler, switching
    lam, db = fit_fig4.load_points()
    rms = fit_fig4.rms_db(fit_fig4.mesh_t20_model, lam, db,
                          coupler.DC_LAMBDA_3DB, coupler.DC_SLOPE,
                          switching.FIG4D_FLOOR_DB)
    assert rms <= 2.0


def test_fig4e_digitized_csv_is_readable_and_on_scale():
    """The digitized Fig 4e points parse, are ordered, and lie inside the panel's axes.

    Fig 4e's axes run 1550-1590 nm by 0 to -25 dB (read in the figure and recorded in the
    CSV header). A point outside that box would mean the pixel-to-data mapping was wrong,
    which no fit downstream would detect on its own.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4
    csv = os.path.join(os.path.dirname(__file__), "..", "data",
                       "fig4e_bar_digitized.csv")
    lam, db = fit_fig4.load_points(csv)
    assert lam.size >= 25
    assert np.all(np.diff(lam) > 0)
    assert lam.min() >= 1550.0 and lam.max() <= 1590.0
    assert np.all(db <= 0.0) and np.all(db >= -25.0)



def test_fig4e_diagonal_csv_is_readable_and_on_scale():
    """The digitized Fig 4e diagonals parse, are ordered, and lie inside the panel's axes.

    The four traces come from four different sub-panels, each with its own pixel-to-data
    fit, so a mis-anchored panel would put one column on a different scale from the other
    three. Nothing downstream would reveal that: the diagonals feed a comparison with the
    paper's insertion-loss range, not a fit, and a shifted column would simply widen the
    range. The through paths also have to sit far above the bar-state leakage of the same
    panel, which is what separates a diagonal from an off-diagonal in the first place.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    lam, cols = fit_fig4e.load_diagonals()
    assert lam.size >= 15
    assert np.all(np.diff(lam) > 0)
    assert lam.min() >= 1550.0 and lam.max() <= 1590.0
    assert set(cols) == set(fit_fig4e.DIAG_NAMES)
    for name, db in cols.items():
        assert db.size == lam.size
        assert np.all(db <= 0.0) and np.all(db >= -25.0), name
        # an intended path, not leakage: the T32 band in the same figure sits below -19 dB
        assert db.max() > -5.0 and db.min() > -12.0, name


def test_fig4e_diagonal_paper_comparison_is_not_a_constant_offset():
    """The two ends of the digitized range must be compared with the paper's separately.

    A constant calibration offset on the digitized dB scale would move both ends of the
    range by the same amount. Reporting only one end, or only the midpoint, would hide
    whether that is what the disagreement is; this pins the two-ended comparison that
    report v9 rests on.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    d = fit_fig4e.diagonal_summary(verbose=False)
    assert d["paper_range_db"] == [-2.99, -1.85]
    for key in ("combined", "combined_continuous"):
        c = d[key]
        lo, hi = c["range_db"]
        assert lo < hi <= 0.0
        assert abs(c["most_lossy_end_minus_paper_db"] - (lo + 2.99)) < 1e-9
        assert abs(c["least_lossy_end_minus_paper_db"] - (hi + 1.85)) < 1e-9
        # the ends do not move together, so the gap is not a constant offset
        assert c["end_difference_db"] > 0.3


def test_fig4e_sigma_split_falls_as_the_reported_percentile_rises():
    """The percentile scan has to be monotonic, or the number it produces is meaningless.

    bar_model reports the pct-th quantile of the fabrication ensemble, and that quantile
    rises with pct at any fixed spread. Matching the same measured level therefore needs
    less spread at a higher percentile, so sigma_split must fall as pct rises. If it did
    not, the scan would not be measuring the modelling choice it claims to measure, and
    the range report v9 quotes as the headline uncertainty would be noise. Run at a small
    ensemble because the direction, not the value, is what is asserted.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    lam, db = fit_fig4e.load_points()
    vals = [fit_fig4e.fit_one("split", lam, db, n_real=200, pct=p)["value"]
            for p in (75.0, 90.0, 99.0)]
    assert np.all(np.diff(vals) < 0), vals
    assert vals[0] > 2 * vals[-1]      # the scan spans a factor of more than two


def test_fig4e_sensitivity_block_is_self_consistent():
    """The keys the report quotes must agree with the scan they are derived from.

    The range across the scan and the offset test is what the report quotes as the spread
    the panel is compatible with, and the reason the fitted value was not adopted. That is
    only honest if the range really does cover every variant and really is far wider than
    the one bootstrap interval still computed, so both are checked here rather than left
    to the prose. The scan itself is no longer bootstrapped, and the interval comparison
    is therefore driven entirely by the adopted_boot the caller supplies.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    lam, db = fit_fig4e.load_points()
    s = fit_fig4e.sensitivity(lam, db, pcts=(90.0, 99.0), n_real=200, verbose=False)
    vals = [v["sigma_split"] for v in s["percentile_scan"].values()]
    vals.append(s["offset_test_sigma_split"])
    lo, hi = s["sigma_split_full_range"]
    assert lo == min(vals) and hi == max(vals)
    assert s["offset_test_db"] < 0.0        # the digitized scale reads high, not low
    assert s["scan_is_bootstrapped"] is False
    for entry in s["percentile_scan"].values():
        assert set(entry) == {"pct", "sigma_split", "se", "rms_db"}, entry
    # without an adopted-fit interval the comparison keys are absent, not invented
    assert s["range_over_bootstrap_factor"] is None
    assert s["adopted_bootstrap_param"] is None

    s2 = fit_fig4e.sensitivity(lam, db, pcts=(90.0, 99.0), n_real=200, verbose=False,
                               adopted_boot={"param_p05": 0.0180, "param_p95": 0.0184,
                                             "n_boot": 500})
    assert s2["range_over_bootstrap_factor"] > 1.0


def test_fig4e_model_is_flat_against_the_digitized_curve():
    """The bar model must be recorded as reproducing the level and not the structure.

    This is the claim report v9 makes about what the panel constrains, and it is the kind
    of claim that quietly stops being true: a later change to the coupler dispersion or to
    the fitted spread could give the model real wavelength structure, and then the report
    would be describing a model that no longer exists. The numbers are loose because the
    assertion is about the size of the effect, not its value.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    sc = fit_fig4e.shape_check(n_real=400, verbose=False)
    assert sc["data_ptp_db"] > 1.0
    assert sc["model_ptp_db"] < 0.05 * sc["data_ptp_db"]
    # no meaningful RMS advantage over the best constant, at the stated point uncertainty
    assert abs(sc["rms_advantage_db"]) < 0.1 * sc["point_sd_db"]


def test_bar_il_vs_fig4e_has_four_ports_on_the_panel_scale():
    """The per-path insertion-loss comparison must cover all four ports and stay on scale.

    Each digitized value in this block has to be a reading from the Fig 4e panel, whose
    axes run 0 to -25 dB, and there has to be one per input port. A silently short block
    would still produce a mean difference, and the report would quote it as a four-path
    comparison when it was fewer; a value off the panel scale would mean the diagonal CSV
    was paired with the wrong column or the wrong wavelength window.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    b = fit_fig4e.bar_il_vs_digitized(verbose=False)
    assert len(b["per_port"]) == 4
    assert [p["in_port"] for p in b["per_port"]] == [0, 1, 2, 3]
    for p in b["per_port"]:
        assert p["in_port"] == p["out_port"]          # the all-bar intended path
        assert -25.0 <= p["digitized_db"] <= 0.0, p
        assert -25.0 <= p["digitized_min_db"] <= p["digitized_max_db"] <= 0.0, p
        assert p["n_points"] == b["n_wavelengths"]
    # the comparison is the continuous segment only: the legend box hides the rest
    assert b["band_nm"][1] <= fit_fig4e.DIAG_CONTINUOUS_MAX_NM


def test_bar_il_comparison_does_not_depend_on_the_fabrication_spread():
    """This comparison must be a test of the loss constants, not of SIGMA_SPLIT.

    switching.fabric_matrix uses nominal 50:50 couplers, so the intended-path loss is set
    by the propagation and coupler excess-loss constants alone. That is what lets report
    v10 discuss this block next to the paper's quoted range without the assumed spread
    being an input to it. If a later change routed this through power_spectra instead, the
    numbers would move with SIGMA_SPLIT and that claim would quietly stop being true.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    from lightin import switching
    base = fit_fig4e.bar_il_vs_digitized(verbose=False)
    keep = switching.SIGMA_SPLIT
    switching.SIGMA_SPLIT = 0.07          # the top of the Fig 4e percentile-scan range
    try:
        moved = fit_fig4e.bar_il_vs_digitized(verbose=False)
    finally:
        switching.SIGMA_SPLIT = keep
    for a, b in zip(base["per_port"], moved["per_port"]):
        assert a["model_db"] == b["model_db"], (a, b)

def test_fig4e_cells_match_the_shipped_mzi():
    """fit_fig4e._cell is mzi_single_theta over a whole ensemble; check it cell by cell.

    The bootstrap calls the bar model tens of thousands of times, so the per-cell Python
    loop was replaced by one broadcast expression. That rewrite is only safe if it is the
    same arithmetic, which nothing downstream would reveal: a wrong cell would still give
    a smooth, plausible, fittable curve.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    from lightin.coupler import mzi_single_theta, DC_LAMBDA_3DB, DC_SLOPE
    rng = np.random.default_rng(3)
    ka = np.clip(rng.normal(0.5, 0.05, size=(2, 6)), 0.3, 0.7)
    kb = np.clip(rng.normal(0.5, 0.05, size=(2, 6)), 0.3, 0.7)
    ph = rng.normal(0.0, 0.05, size=(2, 6))
    lam = np.array([1550.0, 1565.0, 1589.0])
    dl = DC_SLOPE * (lam - DC_LAMBDA_3DB)
    for m in range(6):
        got = fit_fig4e._cell(ka[:, m], kb[:, m], ph[:, m], dl)
        for r in range(2):
            for li, x in enumerate(lam):
                want = mzi_single_theta(switching.THETA_BAR, x, kappa0=ka[r, m],
                                        slope=DC_SLOPE, excess_loss_db=0.1,
                                        kappa0_b=kb[r, m], arm_phase_err=ph[r, m],
                                        lam0=DC_LAMBDA_3DB)
                assert np.allclose(got[r, li], want, atol=1e-14)


def test_fig4e_bar_model_matches_the_shipped_mesh():
    """One realisation of the bar model must be the mesh switching.py already ships.

    At n_real=1 and seed 0 the model draws the same splits and arm phases
    switching.power_spectra draws, so its T32 ratio must equal that mesh's, to machine
    precision. This is what ties the fitted spread to the module the results come from.
    """
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4e
    lam = np.array([1550.0, 1560.0, 1575.0, 1589.0])
    T, _ = switching.power_spectra("bar", lam, seed=0)
    want = T[fit_fig4e.OUT_PORT, fit_fig4e.IN_PORT] / T[:, fit_fig4e.IN_PORT].sum(axis=0)
    got = fit_fig4e._bar_ensemble(lam, switching.SIGMA_SPLIT, switching.SIGMA_PHASE,
                                  n_real=1, seed=0)[0]
    assert np.allclose(got, want, rtol=1e-12, atol=0)


def test_energy_paper_derivation():
    from lightin import throughput
    te = throughput.reproduce(verbose=False)
    assert abs(te["P_total_W"] - 1.8) < 1e-6          # 40 MZIs x 45 mW
    assert abs(te["energy_pj_per_mac"] - 1.875) < 1e-3


def test_square_mesh_wirings_conserve_energy():
    # the wiring is a stated guess, so energy conservation is the one check that would
    # catch a mis-wired vertex: a node joining three ports leaks or creates power
    import numpy as _np
    from lightin import square_mesh
    from lightin.recirculating import unitarity_check
    for wiring in (square_mesh.WIRING_A, square_mesh.WIRING_B):
        mesh = square_mesh.build_mesh(_np.zeros(40), wiring)
        assert unitarity_check(mesh, 1560.0) < 1e-12


def test_connect_rejects_reused_port():
    from lightin import recirculating
    c = recirculating.Circuit()
    for k in range(3):
        c.add_puc(k, recirculating.textbook_coupler(0.7))
    c.connect((0, "R", 0), (1, "L", 0), 100.0)
    with pytest.raises(ValueError, match=r"already connected"):
        c.connect((0, "R", 0), (2, "L", 0), 100.0)


def test_square_mesh_orbits_partition_the_cells():
    from lightin import square_mesh
    orbits = square_mesh.edge_orbits()
    assert sum(len(o) for o in orbits) == 40
    assert sorted(k for o in orbits for k in o) == list(range(40))
    assert all(len(o) == 4 for o in orbits)          # no edge is fixed by a quarter turn


def test_only_wiring_a_is_rotation_equivariant():
    # the PUF design needs the quarter-turn symmetry; no turn-first rule can have it,
    # because the rotation swaps the two all-turn matchings at a degree-4 vertex
    from lightin import square_mesh
    assert square_mesh.wiring_is_rotation_equivariant(square_mesh.WIRING_A)
    assert not square_mesh.wiring_is_rotation_equivariant(square_mesh.WIRING_B)


def test_ppuf_recirc_nominal_pairs_are_degenerate():
    # the symmetry the preprint's PUF rests on: with no fabrication error every compared
    # output pair is exactly equal, so the response comes only from the spread
    import numpy as _np
    from lightin import ppuf_recirc
    rng = _np.random.default_rng(0)
    for _name, wiring in ppuf_recirc.wirings():
        for _ in range(3):
            ch = rng.integers(0, 2, ppuf_recirc.n_challenge_bits())
            bits, ties = ppuf_recirc.response(ch, _np.zeros(40), wiring=wiring)
            assert ties == len(bits)


def test_ppuf_recirc_uses_half_turn_orbits():
    # the quarter turn cannot preserve a port set on two opposite edges, so the design is
    # built on the half turn: 20 orbits of two cells, 20 challenge bits, 9 response bits
    from lightin import ppuf_recirc, square_mesh
    orbs = square_mesh.half_turn_orbits()
    assert len(orbs) == 20 and all(len(o) == 2 for o in orbs)
    assert sorted(k for o in orbs for k in o) == list(range(40))
    assert ppuf_recirc.n_challenge_bits() == 20
    for _name, wiring in ppuf_recirc.wirings():
        assert ppuf_recirc.n_response_bits(wiring) == 9
        assert ppuf_recirc.live_pairs(wiring) == 9


def test_ppuf_recirc_responds_to_manufacturing_spread():
    """Same three assertions as the feed-forward PUF test, on the recirculating mesh."""
    from lightin import ppuf_recirc
    for _name, wiring in ppuf_recirc.wirings():
        lo, hi = ppuf_recirc.sensitivity_sweep(sigmas=(0.001, 1.05), n_dies=20,
                                               n_challenges=32, wiring=wiring)
        assert 0.40 <= hi["uniqueness"] <= 0.60
        assert hi["tie_fraction"] < 0.05
        assert lo["uniqueness"] < 0.20 or lo["reliability"] >= 0.5 * lo["uniqueness"]


def test_square_mesh_straight_wiring_decouples_the_mesh():
    """Records why the straight-through rule fails, not a property of the lattice.

    WIRING_A joins two edge-ends only waveguide-0-to-waveguide-0 and 1-to-1, which treats
    a vertex as having one port per incident edge. An interior vertex really has eight
    ports, two per end, and the matchings that mix the waveguides are exactly the ones
    that connect the mesh (`lightin/wiring_search.py`). Under the four-port simplification
    the straight rule sends light straight through every interior vertex, so the mesh
    falls into independent rows and columns and WIRING_A reaches 4 of 40 cells. This
    records that simplification; it is not evidence about wirings in general.
    """
    import numpy as _np
    from lightin import square_mesh
    mesh = square_mesh.build_mesh(_np.zeros(40), square_mesh.WIRING_A)
    adj = {}
    for (a, b, _length) in mesh.connections:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    for k in range(40):
        ps = [(k, sd, wg) for sd in ("L", "R") for wg in (0, 1)]
        for q in ps:
            adj.setdefault(q, []).extend(x for x in ps if x != q)
    start = square_mesh.boundary_ports(square_mesh.WIRING_A)[0]
    seen, stack = {start}, [start]
    while stack:
        q = stack.pop()
        for x in adj.get(q, []):
            if x not in seen:
                seen.add(x); stack.append(x)
    assert len({q[0] for q in seen}) == 4


def test_interior_vertex_has_eight_ports():
    # the count the earlier enumeration got wrong: each incident PUC end carries two
    # waveguides, so a vertex matching is over 8 ports and there are 7!! = 105 of them
    from lightin import square_mesh
    ends = square_mesh.incident_ends(2, 2)
    assert len(ends) == 4
    assert len({(pid, side, wg) for (pid, side) in ends.values() for wg in (0, 1)}) == 8
    assert len(list(square_mesh.perfect_matchings(square_mesh.slots()))) == 105


def test_half_turn_invariant_wirings_connect_the_mesh():
    # 12 of the 25 half-turn-invariant rules reach every cell with both beams able to
    # interfere, which is what the four-port simplification had hidden
    from lightin import wiring_search
    rows = wiring_search.search_report()
    assert len(rows) == 25
    good = [info for (_i, _r, info) in rows
            if info["n_cells_reachable"] == 40 and info["beams_interfere"]]
    assert len(good) >= 2
    best = rows[0][2]
    assert best["n_cells_reachable"] == 40 and best["beams_interfere"]
    assert best["unitarity_dev"] < 1e-12


def test_io_mesh_has_twenty_half_turn_symmetric_ports():
    # the preprint's port count and placement: 20 gratings, ten on each opposite edge,
    # and the set must map onto itself under the half turn or the PUF pairing cannot form
    import numpy as _np
    from lightin import square_mesh, wiring_search
    for _name, rule in wiring_search.selected():
        gp = square_mesh.grating_ports(rule)
        assert len(gp) == 20
        top = [q for q in gp if square_mesh.vertex_of_port(q)[0] == 0]
        bot = [q for q in gp if square_mesh.vertex_of_port(q)[0] == square_mesh.N_CELLS]
        assert len(top) == 10 and len(bot) == 10
        assert {square_mesh.half_turn_port(q) for q in gp} == set(gp)
        mesh = square_mesh.build_io_mesh(_np.zeros(40), rule)
        assert len(mesh.optical_ports) == 20


def test_io_mesh_conserves_energy_once_terminations_are_counted():
    import numpy as _np
    from lightin import square_mesh, wiring_search
    for _name, rule in wiring_search.selected():
        mesh = square_mesh.build_io_mesh(_np.zeros(40), rule, loss_db_cm=0.0)
        inj = {mesh.optical_ports[0]: 1.0}
        _opt, _term, total = square_mesh.energy_audit(mesh, 1560.0, inj)
        assert abs(total - 1.0) < 1e-12


def test_recirc_puf_wirings_agree():
    """The two stated wirings must not disagree about the PUF.

    Every number from this mesh is conditional on a wiring nobody has the layout for, so
    the honest check is that the conclusion does not depend on which of the two is used.
    """
    from lightin import ppuf_recirc
    (_n1, w1), (_n2, w2) = ppuf_recirc.wirings()
    a = ppuf_recirc.evaluate(n_dies=10, n_challenges=16, wiring=w1)
    b = ppuf_recirc.evaluate(n_dies=10, n_challenges=16, wiring=w2)
    assert abs(a["uniqueness"] - b["uniqueness"]) < 0.05


def test_population_sweep_reports_a_spread():
    # a PUF metric on a finite die sample has a sampling spread; the sweep must report it
    # rather than hand back one seed's value
    from lightin import ppuf, ppuf_recirc
    ff = ppuf.population_sweep(seeds=range(3), n_dies=8, n_challenges=8)
    assert ff["n_seeds"] == 3 and len(ff["uniqueness_per_seed"]) == 3
    assert ff["uniqueness_std"] > 0.0
    for key in ("uniqueness", "uniformity", "reliability"):
        assert abs(ff[key + "_mean"] - np.mean(ff[key + "_per_seed"])) < 1e-12
    rc = ppuf_recirc.population_sweep(seeds=range(3), n_dies=6, n_challenges=6)
    assert rc["n_seeds"] == 3 and rc["uniqueness_std"] > 0.0


def test_noise_sweep_drives_reliability_not_uniqueness():
    """Reliability is set by the assumed measurement noise; uniqueness is not.

    Uniqueness, uniformity and the tie fraction come from the noise-free reference
    response, so they must not move with the noise. If they do, the noise is leaking into
    the reference and the reliability number means something else.
    """
    from lightin import ppuf_recirc
    rows = ppuf_recirc.noise_sweep(sigmas=(0.002, 0.05), n_dies=8, n_challenges=8, seed=1)
    lo, hi = rows
    assert hi["reliability"] > lo["reliability"]
    assert lo["uniqueness"] == hi["uniqueness"]
    assert lo["tie_fraction"] == hi["tie_fraction"]


def test_ppuf_real_arm_length_distribution():
    # N(-0.08, 0.11) um -> rad. The mean is negative: the preprint
    # (arXiv:2504.01463v2 section 2.5) gives mu = -0.08 um, and the sign is pinned here so
    # that losing it again fails rather than shifting the metrics quietly.
    from lightin import ppuf
    mu, sig = ppuf.phase_stats_from_arm_length()
    assert -0.9 < mu < -0.6 and 0.9 < sig < 1.2

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t(); print(f"PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
