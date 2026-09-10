"""
Fit the coupler dispersion to the digitized LightIN Fig 4d (all-cross) T20 crosstalk
curve, and overlay the fitted model. Run: PYTHONPATH=. python3 scripts/fit_fig4.py

The digitized data (data/fig4d_T20_digitized.csv) was extracted from the published
figure by colour segmentation, with the dB scale anchored to figure-read endpoints
(~+/-2 dB). Cross-state crosstalk has a floor (the ~-25 dB minimum from fabrication /
measurement), so the model is  10*log10[(1-2*kappa)^2 + floor],  with
kappa(lambda) = sin^2(arcsin(sqrt(0.5)) + slope*(lambda - lambda0)).
"""
import os
import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
CSV = os.path.join(HERE, "..", "data", "fig4d_T20_digitized.csv")
FIG = os.path.join(HERE, "..", "figures", "fig4_digitized.png")


def crosstalk_model(lam, lam0, slope, floor_db):
    a0 = np.arcsin(np.sqrt(0.5))
    k = np.sin(a0 + slope * (lam - lam0)) ** 2
    return 10 * np.log10((1 - 2 * k) ** 2 + 10 ** (floor_db / 10))


def main():
    lam, db = [], []
    with open(CSV) as f:
        for line in f:
            if line.startswith("#") or line.startswith("wavelength"):
                continue
            a, b = line.strip().split(",")
            lam.append(float(a)); db.append(float(b))
    lam = np.array(lam); db = np.array(db)

    popt, _ = curve_fit(crosstalk_model, lam, db,
                        p0=[1568.0, 0.0045, -25.0], maxfev=40000)
    lam0, slope, floor = popt
    rms = float(np.sqrt(np.mean((db - crosstalk_model(lam, *popt)) ** 2)))
    print(f"Fit to digitized Fig 4d T20 crosstalk:")
    print(f"  coupler 3-dB wavelength lambda0 = {lam0:.1f} nm")
    print(f"  dispersion slope                = {slope:.4f} rad/nm  "
          f"(literature/default was 0.004)")
    print(f"  crosstalk floor                 = {floor:.1f} dB")
    print(f"  fit RMS                         = {rms:.2f} dB")

    lf = np.linspace(lam.min(), lam.max(), 400)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.scatter(lam, db, s=26, color="#C44E52", zorder=3,
               label="digitized Fig 4d $T_{20}$ (±2 dB)")
    ax.plot(lf, crosstalk_model(lf, *popt), color="#4C72B0", lw=2,
            label=(f"CMT coupler fit\n$\\lambda_0$={lam0:.1f} nm, "
                   f"slope={slope:.4f} rad/nm\nRMS={rms:.2f} dB"))
    ax.axhline(-15, color="grey", ls=":", lw=1)
    ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Crosstalk (dB)")
    ax.set_title("Coupler dispersion fitted to the chip's measured crosstalk\n"
                 "(LightIN Fig 4d, all-cross $T_{20}$; digitized)", fontsize=10)
    ax.legend(fontsize=8); ax.set_ylim(-27, -10)
    fig.tight_layout(); fig.savefig(FIG, dpi=140)
    print(f"  wrote {os.path.abspath(FIG)}")
    return {"lambda0_nm": float(lam0), "slope_rad_nm": float(slope),
            "floor_db": float(floor), "rms_db": rms}


if __name__ == "__main__":
    main()
