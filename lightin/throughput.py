"""
Throughput (TOPS) and energy-per-MAC, using the LightIN paper's exact derivation.

Both numbers are now grounded in the paper + supplementary (Note 3), not assumptions.

ENERGY (Supplementary Note 3, exact):
  - A pi phase shift needs an averaged 3 V across a 100 Ohm heater -> P_pi = V^2/R = 90 mW.
  - Because the MZI has a single-arm phase shifter, theta in [0, pi] with expectation pi/2,
    and thermo-optic phase is proportional to power, so the average power per MZI is
    90 mW * (E[theta]/pi) = 90 * 0.5 = 45 mW.
  - 40 MZIs -> total static power = 1.8 W.
  - Energy efficiency = total power / MAC rate.
    MAC rate = TOPS / 2 ops-per-MAC = 1.92e12 / 2 = 0.96e12 MAC/s.
    Energy = 1.8 / 0.96e12 = 1.875 pJ/MAC.   (matches the paper exactly)

THROUGHPUT (Supplementary Note 3, exact convention):
  speed = (Complex 4x4 x Real 4x1 in the P-FPGA + squared addition in the PDs)
          x 2 directions x 10 GBaud = 1.92 TOPS.
  i.e. 96 operations per matrix-vector product, x2 directions, x10 GBaud.
"""


def reproduce(verbose=True):
    V_pi = 3.0           # V, averaged voltage for a pi shift (Supp Note 3)
    R = 100.0            # Ohm, heater resistance (Supp Note 3)
    P_pi = V_pi ** 2 / R                 # 90 mW for pi
    E_theta_over_pi = 0.5                # theta ~ U[0, pi], expectation pi/2
    P_avg_per_mzi = P_pi * E_theta_over_pi   # 45 mW
    n_mzi = 40
    P_total = P_avg_per_mzi * n_mzi      # 1.8 W

    tops = 1.92                          # paper, with stated convention
    ops_per_mac = 2
    mac_rate = tops * 1e12 / ops_per_mac # 0.96e12 MAC/s
    energy_pj_per_mac = P_total / mac_rate * 1e12

    # the paper's explicit op count: 96 ops/MVM x 2 directions x 10 GBaud
    ops_per_mvm = 96
    tops_check = ops_per_mvm * 2 * 10e9 / 1e12

    if verbose:
        print(f"[energy] P_pi = {V_pi}^2/{R:.0f} = {P_pi*1e3:.0f} mW; "
              f"avg/MZI = {P_avg_per_mzi*1e3:.0f} mW; 40 MZIs -> {P_total:.2f} W")
        print(f"[energy] {P_total:.2f} W / {mac_rate:.2e} MAC/s = "
              f"{energy_pj_per_mac:.3f} pJ/MAC  (paper: 1.875 pJ/MAC)")
        print(f"[throughput] convention (96 ops/MVM x 2 dir x 10 GBaud) = {tops_check:.2f} TOPS "
              f"(paper: 1.92 TOPS)")
    return {"P_pi_mW": P_pi * 1e3, "P_avg_per_mzi_mW": P_avg_per_mzi * 1e3,
            "P_total_W": P_total, "mac_rate": mac_rate,
            "energy_pj_per_mac": energy_pj_per_mac, "tops": tops_check}


if __name__ == "__main__":
    reproduce()
