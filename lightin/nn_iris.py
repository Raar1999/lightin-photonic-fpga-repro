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
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

N_RESTARTS = 15     # random restarts of the offline training, shared by model and control


def _train_test(seed, complex_features=True):
    """The 70/30 stratified split used everywhere here, with random_state=seed.

    Returns (X, y, Xtr, Xte, ytr, yte) over the four standardized features, complex-cast
    for the photonic layer and left real for the logistic baseline. The partition depends
    only on y, test_size and random_state, so every function below sees the same split.
    """
    data = load_iris()
    y = data.target.astype(int)
    Xs = StandardScaler().fit_transform(data.data.astype(float))
    X = Xs.astype(complex) if complex_features else Xs
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3,
                                          random_state=seed, stratify=y)
    return X, y, Xtr, Xte, ytr, yte


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


def train(seed=0, restarts=N_RESTARTS):
    """Offline-train the photonic layer and its readout on one 70/30 split.

    restarts is the number of random restarts of the non-convex fit; it defaults to
    N_RESTARTS, the value the reported results use. Lowering it makes the fit cheaper
    and, because the best restart is kept, can only lower the accuracy on average, so a
    reduced-restart accuracy is a lower bound on the reported one rather than a
    different quantity.
    """
    # 4 features encoded as complex amplitudes (real-valued here)
    Xc, y, Xtr, Xte, ytr, yte = _train_test(seed)

    N, n_classes = 4, 3
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(restarts):
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


def _accuracy(p, X, y, N=4, n_classes=3):
    probs, _ = _forward(p, X, N, n_classes)
    return float(np.mean(probs.argmax(1) == y))


def _spread(full, test):
    """Mean, standard deviation and per-seed values of the two accuracies."""
    full = np.asarray(full, dtype=float)
    test = np.asarray(test, dtype=float)
    return {
        "full_acc_mean": float(full.mean()), "full_acc_std": float(full.std()),
        "test_acc_mean": float(test.mean()), "test_acc_std": float(test.std()),
        "full_acc_per_seed": [float(v) for v in full],
        "test_acc_per_seed": [float(v) for v in test],
    }


def seed_sweep(seeds=range(10)):
    """Accuracy of the trained photonic layer across seeds.

    The seed drives both the split and the random restarts, so the spread here is the
    honest uncertainty on a single-seed number like the paper's 94.67%.
    """
    full, test = [], []
    for s in seeds:
        res = train(seed=s)
        full.append(res["full_acc"]); test.append(res["test_acc"])
    return _spread(full, test)


def identity_control(seeds=range(10)):
    """Same readout, unitary frozen to the identity.

    With H = 0 the photonic layer is W = I, so the detected intensities are just the
    squared standardized features and only the linear readout is trained. Accuracy above
    this line is what the programmable unitary actually contributes.
    """
    N, n_classes = 4, 3
    n_readout = n_classes * N + n_classes

    def readout_loss(q, X, y):
        return _loss(np.concatenate([np.zeros(N * N), q]), X, y, N, n_classes)

    full, test = [], []
    for s in seeds:
        Xc, y, Xtr, Xte, ytr, yte = _train_test(s)
        rng = np.random.default_rng(s)
        best = None
        for _ in range(N_RESTARTS):
            q0 = rng.uniform(-1, 1, n_readout)
            sol = minimize(readout_loss, q0, args=(Xtr, ytr),
                           method="L-BFGS-B", options={"maxiter": 4000})
            if best is None or sol.fun < best.fun:
                best = sol
        p = np.concatenate([np.zeros(N * N), best.x])
        full.append(_accuracy(p, Xc, y, N, n_classes))
        test.append(_accuracy(p, Xte, yte, N, n_classes))
    return _spread(full, test)


def logistic_baseline(seeds=range(10)):
    """Plain multinomial logistic regression on the same features and the same splits.

    A four-feature linear classifier is the threshold the photonic layer has to beat for
    the demonstration to be about photonics rather than about Iris being easy.
    """
    full, test = [], []
    for s in seeds:
        Xs, y, Xtr, Xte, ytr, yte = _train_test(s, complex_features=False)
        clf = LogisticRegression(max_iter=5000).fit(Xtr, ytr)
        full.append(float(clf.score(Xs, y)))
        test.append(float(clf.score(Xte, yte)))
    return _spread(full, test)


def _print_spread(label, d):
    print(f"[Iris {label}] full-set {100*d['full_acc_mean']:.2f}% +/- "
          f"{100*d['full_acc_std']:.2f}%,  held-out {100*d['test_acc_mean']:.2f}% +/- "
          f"{100*d['test_acc_std']:.2f}%  (n={len(d['full_acc_per_seed'])} seeds)")


def run(verbose=True, seeds=range(10)):
    """Train once at seed 0, then sweep the photonic layer and both controls over seeds.

    seeds is shared by the sweep and the two controls so their per-seed lists line up
    element by element and can be compared seed against seed.
    """
    res = train(seed=0)
    res["seed_sweep"] = seed_sweep(seeds)
    res["identity_control"] = identity_control(seeds)
    res["logistic_baseline"] = logistic_baseline(seeds)
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
        _print_spread("across seeds     ", res["seed_sweep"])
        _print_spread("identity control ", res["identity_control"])
        _print_spread("logistic baseline", res["logistic_baseline"])
    return res


if __name__ == "__main__":
    run()
