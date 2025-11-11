import numpy as np

def nm_to_inv_cm(lambda_nm):
    """
    Convert wavelength from nanometers (nm) to wavenumber (cm⁻¹).

    Formula: 𝜈~tilde~ [cm⁻¹] = 10⁷ / λ[nm]

    Accepts: float | int | array-like
    Returns: numpy.ndarray (or float if you pass a scalar)
    """
    arr = np.asarray(lambda_nm, dtype=float)
    return (1e7 / arr) if arr.ndim else float(1e7 / arr)


def place_in_string(values, positions, specs=None, total_width=None):
    """
    Right-align each value so it ENDS at positions[i] (1-based columns).
    positions must be strictly increasing.
    """
    if len(values) != len(positions):
        raise ValueError("values and positions must match in length")
    if any(b <= a for a, b in zip(positions, positions[1:])):
        raise ValueError("positions must be strictly increasing")

    specs = specs or [""] * len(values)
    widths = [positions[0]] + [b - a for a, b in zip(positions, positions[1:])]

    parts = []
    for val, w, sp in zip(values, widths, specs):
        txt = format(val, sp)
        if len(txt) > w:
            raise ValueError(f"value {txt!r} wider than its field width {w}")
        parts.append(txt.rjust(w))

    s = "".join(parts)
    return s if total_width is None else s.ljust(total_width)


