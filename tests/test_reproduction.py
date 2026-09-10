"""
Verification tests for the LightIN reproduction.
Run directly:  PYTHONPATH=. python3 tests/test_reproduction.py
Or with pytest: PYTHONPATH=. pytest -q
"""

import numpy as np
from lightin import puc, metrics, unitary, nonunitary, nn_iris, ppuf, mrm, switching, throughput


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
    res = nn_iris.train(seed=0)
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


def test_coupler_dispersion_fit():
    from lightin import coupler
    lam, k = coupler._demo_measured_dataset(seed=3)
    k0, slope, rms = coupler.fit_dc_dispersion(lam, k)
    assert abs(k0 - 0.5) < 0.05 and rms < 0.01                     # recovers parameters


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
    # the digitized chip crosstalk curve is present and the coupler fit is sensible
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import fit_fig4
    res = fit_fig4.main()
    assert 1560 < res["lambda0_nm"] < 1580          # coupler 3-dB wavelength from Fig 4d
    assert 0.001 < res["slope_rad_nm"] < 0.008       # dispersion slope, near literature
    assert res["rms_db"] < 2.0                        # fit within digitization uncertainty


def test_energy_paper_derivation():
    from lightin import throughput
    te = throughput.reproduce(verbose=False)
    assert abs(te["P_total_W"] - 1.8) < 1e-6          # 40 MZIs x 45 mW
    assert abs(te["energy_pj_per_mac"] - 1.875) < 1e-3


def test_ppuf_real_arm_length_distribution():
    from lightin import ppuf
    mu, sig = ppuf.phase_stats_from_arm_length()      # N(0.08, 0.11) um -> rad
    assert 0.6 < mu < 0.9 and 0.9 < sig < 1.2

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
