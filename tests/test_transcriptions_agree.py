"""
A paper value transcribed into more than one place must read the same in all of them.

Run directly:  PYTHONPATH=. python3 tests/test_transcriptions_agree.py
Or with pytest: PYTHONPATH=. pytest -q

`tests/test_constants_documented.py` checks each documented constant against the module
that holds it. That is one document against one module, and it says nothing about a value
the code records twice. Several of the paper's numbers are recorded twice: the square-mesh
side length is `coupler.SQUARE_SIDE_UM` and again `square_mesh.SIDE_UM`; the matrix design
wavelength is `coupler.LAMBDA0` and again `ppuf_recirc.LAMBDA_NM`; the phase index and the
propagation loss are module constants in `coupler` and default arguments of the ring and
mesh builders in `recirculating` and `square_mesh`.

§6.3 documents one of each pair, so editing the other leaves every document check green
while the two models quietly disagree about the same chip. This test reads them back
against each other.

The default arguments are read from the live signatures rather than from the source text,
so renaming a function or moving it between modules does not hide one.
"""

import importlib
import inspect
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "lightin"

# One paper quantity, every module-level constant that records it.
DUPLICATED_CONSTANTS = {
    "square-mesh unit side (um)": [
        ("lightin.coupler", "SQUARE_SIDE_UM"),
        ("lightin.square_mesh", "SIDE_UM"),
    ],
    "matrix design wavelength (nm)": [
        ("lightin.coupler", "LAMBDA0"),
        ("lightin.ppuf_recirc", "LAMBDA_NM"),
    ],
}

# A default argument of this name records the paper value the named constant holds.
SHARED_DEFAULTS = {
    "n_eff": ("lightin.coupler", "N_EFF"),
    "loss_db_cm": ("lightin.coupler", "PROP_LOSS_DB_CM"),
    "alpha_db_cm": ("lightin.coupler", "PROP_LOSS_DB_CM"),
}


def modules():
    """Every module of the package, imported."""
    names = sorted(path.stem for path in (ROOT / PACKAGE).glob("*.py")
                   if path.stem != "__init__")
    return [importlib.import_module(f"{PACKAGE}.{name}") for name in names]


def constant(target):
    module, attribute = target
    return getattr(importlib.import_module(module), attribute)


def numeric_defaults():
    """Every numeric default argument in the package, with where it is written.

    Yields (module.function, parameter name, default value).
    """
    found = []
    for module in modules():
        for name, obj in vars(module).items():
            if not (inspect.isfunction(obj) and obj.__module__ == module.__name__):
                continue
            for parameter, spec in inspect.signature(obj).parameters.items():
                default = spec.default
                if isinstance(default, (int, float)) and not isinstance(default, bool):
                    found.append((f"{module.__name__}.{name}", parameter, default))
    return found


def test_duplicated_constants_agree():
    """Where two modules record the same paper value, they record the same number."""
    bad = []
    for quantity, targets in DUPLICATED_CONSTANTS.items():
        values = [(f"{module}.{attribute}", constant((module, attribute)))
                  for module, attribute in targets]
        if len({value for _, value in values}) > 1:
            bad.append((quantity, values))

    if bad:
        rows = "\n".join(
            f"  {quantity}\n" + "\n".join(f"      {name} = {value!r}" for name, value in values)
            for quantity, values in bad
        )
        pytest.fail(
            f"{len(bad)} paper values are recorded twice and the two copies disagree.\n"
            f"Both are transcriptions of the same number, so one of them is now wrong.\n{rows}"
        )


def test_shared_defaults_match_their_constant():
    """A default argument that records a paper value equals the constant that holds it."""
    bad = []
    for where, parameter, default in numeric_defaults():
        target = SHARED_DEFAULTS.get(parameter)
        if target is None:
            continue
        expected = constant(target)
        if default != expected:
            bad.append((where, parameter, default, f"{target[0]}.{target[1]}", expected))

    if bad:
        width = max(len(row[0]) for row in bad)
        rows = "\n".join(
            f"  {where:<{width}}  {parameter}={default!r}  but {name} = {expected!r}"
            for where, parameter, default, name, expected in bad
        )
        pytest.fail(
            f"{len(bad)} default arguments disagree with the constant that records the same "
            f"paper value.\nChange the default to reference the constant, never the other "
            f"way round.\n{rows}"
        )


def test_every_shared_default_is_still_used():
    """A name in SHARED_DEFAULTS that no function uses is a check that has quietly lapsed."""
    used = {parameter for _, parameter, _ in numeric_defaults()}
    unused = sorted(set(SHARED_DEFAULTS) - used)
    if unused:
        rows = "\n".join(f"  {name}" for name in unused)
        pytest.fail(
            f"{len(unused)} shared-default names are no longer any function's parameter, so "
            f"nothing is being compared for them:\n{rows}"
        )


if __name__ == "__main__":
    checked = 0
    for quantity, targets in DUPLICATED_CONSTANTS.items():
        values = {constant(target) for target in targets}
        checked += len(targets)
        print(f"{quantity}: {'agree' if len(values) == 1 else 'DISAGREE'} {sorted(values)}")
    shared = [row for row in numeric_defaults() if row[1] in SHARED_DEFAULTS]
    for where, parameter, default in shared:
        expected = constant(SHARED_DEFAULTS[parameter])
        flag = "ok" if default == expected else "DISAGREES"
        print(f"{where} {parameter}={default!r} vs {expected!r} -- {flag}")
    print(f"{checked} constants and {len(shared)} default arguments compared")
