"""
One-layer unitary neural network for Iris classification (paper Fig. 2o,p).

The chip implements a unitary linear layer; detection is by output intensity (|.|^2),
which supplies the nonlinearity. We train a 4x4 unitary W = expm(iH) offline, read three
output-port intensities as class scores, and classify by softmax. This reproduces the
paper's *offline* training accuracy (it reports 94.67% offline, 93.33% online on-chip;
the online number is a hardware measurement and is not reproducible from the paper).

The trained unitary is realisable on the universal mesh (see lightin.unitary.fit_unitary),
i.e. it corresponds to a set of programmable MZI phases.
"""

import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize
from sklearn.datasets import load_iris
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


def _hermitian_from_params(p, N=4):
    H = np.zeros((N, N), dtype=complex)
    idx = 0
    for i in range(N):
        H[i, i] = p[idx]; idx += 1
    for i in range(N):
        for j in range(i + 1, N):
            re = p[idx]; im = p[idx + 1]; idx += 2
            H[i, j] = re + 1j * im
            H[j, i] = re - 1j * im
    return H


def _forward(p, X, N=4, n_classes=3):
    """Photonic unitary W (4x4) -> detect 4 intensities -> learned linear readout."""
    H = _hermitian_from_params(p[:N * N], N)
    W = expm(1j * H)
    R = p[N * N:N * N + n_classes * N].reshape(n_classes, N)   # readout weights (3x4)
    b = p[N * N + n_classes * N:N * N + n_classes * N + n_classes]
    Z = X @ W.T                       # (samples, N) complex
    inten = np.abs(Z) ** 2            # 4 detected intensities (what the PD measures)
    logits = inten @ R.T + b
    logits -= logits.max(axis=1, keepdims=True)
    e = np.exp(logits)
    return e / e.sum(axis=1, keepdims=True), W


def _n_params(N=4, n_classes=3):
    return N * N + n_classes * N + n_classes


def _loss(p, X, y, N=4, n_classes=3):
    probs, _ = _forward(p, X, N, n_classes)
    n = len(y)
    ll = -np.log(probs[np.arange(n), y] + 1e-12).mean()
    return ll + 1e-4 * np.sum(p ** 2)


def train(seed=0):
    data = load_iris()
    X = data.data.astype(float)
    y = data.target.astype(int)
    Xs = StandardScaler().fit_transform(X)
    # encode 4 features as complex amplitudes (real-valued here)
    Xc = Xs.astype(complex)
    Xtr, Xte, ytr, yte = train_test_split(Xc, y, test_size=0.3,
                                          random_state=seed, stratify=y)

    N, n_classes = 4, 3
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(15):
        p0 = rng.uniform(-1, 1, _n_params(N, n_classes))
        sol = minimize(_loss, p0, args=(Xtr, ytr, N, n_classes),
                       method="L-BFGS-B", options={"maxiter": 4000})
        if best is None or sol.fun < best.fun:
            best = sol
    p = best.x

    def accuracy(Xset, yset):
        probs, _ = _forward(p, Xset, N, n_classes)
        return float(np.mean(probs.argmax(1) == yset))

    probs_all, W = _forward(p, Xc, N, n_classes)
    pred_all = probs_all.argmax(1)

    # column-normalised confusion matrix in percent (columns = true class), like Fig.2o
    cm = np.zeros((n_classes, n_classes))
    for t in range(n_classes):
        mask = (y == t)
        for pr in range(n_classes):
            cm[pr, t] = 100.0 * np.mean(pred_all[mask] == pr)

    return {
        "train_acc": accuracy(Xtr, ytr),
        "test_acc": accuracy(Xte, yte),
        "full_acc": float(np.mean(pred_all == y)),
        "confusion_percent": cm,
        "class_names": list(load_iris().target_names),
        "W": W,
    }


def run(verbose=True):
    res = train(seed=0)
    if verbose:
        print(f"[Iris unitary NN] offline train acc = {100*res['train_acc']:.2f}%  "
              f"(paper offline: 94.67%)")
        print(f"[Iris unitary NN] held-out test acc = {100*res['test_acc']:.2f}%  "
              f"(paper on-chip: 93.33%, hardware-only)")
        print(f"[Iris unitary NN] full-set acc      = {100*res['full_acc']:.2f}%")
        print("[Iris unitary NN] confusion (% of column/true class):")
        names = [n[:9] for n in res["class_names"]]
        print("            " + "  ".join(f"{n:>9s}" for n in names))
        for i, n in enumerate(names):
            row = "  ".join(f"{v:9.1f}" for v in res["confusion_percent"][i])
            print(f"  pred {n:<6s} {row}")
    return res


if __name__ == "__main__":
    run()
