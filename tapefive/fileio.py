import re
import pathlib as pl
from datetime import datetime
import numpy as np
import xarray as xr

def read_tape27(path):
    lines = pl.Path(path).read_text(errors="replace").splitlines()

    # header
    attrs = {}
    m = re.search(r"LBLRTM\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})", lines[1] if len(lines) > 1 else "")
    if m:
        try:
            attrs["lblrtm_timestamp"] = datetime.strptime(
                f"{m.group(1)} {m.group(2)}", "%y/%m/%d %H:%M:%S"
            ).isoformat()
        except Exception:
            attrs["lblrtm_timestamp"] = f"{m.group(1)} {m.group(2)}"

    def gfloat(pat, s): 
        m = re.search(pat, s); 
        return float(m.group(1)) if m else None

    for s in lines[:60]:
        if "INITIAL LAYER" in s and "FINAL LAYER" in s:
            m = re.search(r"INITIAL LAYER\s*=\s*(\d+).+FINAL LAYER\s*=\s*(\d+)", s)
            if m:
                attrs["initial_layer"], attrs["final_layer"] = int(m.group(1)), int(m.group(2))
        if "SECANT" in s: attrs["secant"] = gfloat(r"SECANT\s*=\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)", s)
        if "PRESS" in s: attrs["pressure_mb"] = gfloat(r"PRESS\(MB\)\s*=\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)", s)
        if re.search(r"\bTEMP\b", s): attrs["temperature_k"] = gfloat(r"TEMP\s*=\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)", s)
        if re.search(r"\bDV\b", s): attrs["dv_cm^-1"] = gfloat(r"DV\s*=\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s*CM-1", s)
        if re.search(r"\bV1\b", s): attrs["v1_cm^-1"] = gfloat(r"V1\s*=\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s*CM-1", s)
        if re.search(r"\bV2\b", s): attrs["v2_cm^-1"] = gfloat(r"V2\s*=\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s*CM-1", s)
    attrs["source"] = "LBLRTM TAPE27 (transmittance)"

    # data (two floats per line)
    fp = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s+([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)\s*$")
    x, y = [], []
    for s in lines:
        m = fp.match(s)
        if m:
            x.append(float(m.group(1)))
            y.append(float(m.group(2)))
    if not x:
        raise ValueError("No numeric data found.")

    x = np.asarray(x); y = np.asarray(y)
    idx = np.argsort(x); x, y = x[idx], y[idx]

    ds = xr.Dataset(
        data_vars={"transmittance": ("wavenumber", y, {"units": "1", "long_name": "spectral transmittance"})},
        coords={"wavenumber": ("wavenumber", x, {"units": "cm^-1", "long_name": "wavenumber"})},
        attrs=attrs,
    )
    ds = ds.assign_coords(
        wavelength_nm=("wavenumber", np.where(x > 0, 1e7 / x, np.nan), {"units": "nm", "long_name": "wavelength"})
    )
    return ds



def read_tape12(path: str, var_name: str = "optical_depth", units: str = '1') -> xr.Dataset:
    """
    Read an LBLRTM TAPE12 (Fortran unformatted) binary file and return an xarray.Dataset.

    Returns
    -------
    xarray.Dataset
        Coordinates:
            - wavenumber (cm^-1)
        Data variables:
            - value (float64): spectrum values (e.g., transmittance, radiance, OD)
        Attributes:
            - source, endianness, record_marker_bytes, panel_count, v1_first, v2_last
    """
    import io
    import os
    import struct
    import numpy as np
    import xarray as xr

    def _detect_and_read_records(f: io.BufferedReader):
        """Auto-detect record-marker size (4/8 bytes) and endianness (< or >), then return list of record payloads."""
        file_bytes = f.read()
        for marker_bytes, endian in ((4, "<"), (4, ">"), (8, "<"), (8, ">")):
            try:
                recs = []
                pos = 0
                total = len(file_bytes)
                fmt_char = "I" if marker_bytes == 4 else "Q"
                while pos + marker_bytes <= total:
                    size = struct.unpack_from(endian + fmt_char, file_bytes, pos)[0]
                    pos += marker_bytes
                    if size < 0 or pos + size > total:
                        raise ValueError
                    payload = memoryview(file_bytes)[pos:pos + size].tobytes()
                    pos += size
                    if pos + marker_bytes > total:
                        raise ValueError
                    size2 = struct.unpack_from(endian + fmt_char, file_bytes, pos)[0]
                    pos += marker_bytes
                    if size2 != size:
                        raise ValueError
                    recs.append(payload)
                return recs, marker_bytes, endian
            except Exception:
                continue
        raise ValueError("Unable to detect Fortran record markers / endianness.")

    with open(path, "rb") as f:
        records, marker_bytes, endian = _detect_and_read_records(f)

    wn_blocks = []
    val_blocks = []
    v1_list = []
    v2_list = []
    i = 0
    nrec = len(records)

    # Each panel is: header record (v1, v2, dv, n) followed by a data record of length n*(4 or 8) bytes
    while i < nrec - 1:
        hdr = records[i]
        dat = records[i + 1]

        matched = False
        for fmt, _ in (("ddfi", np.float32), ("dddi", np.float64), ("dddq", np.float64)):
            fmt_full = endian + fmt
            need = struct.calcsize(fmt_full)
            if len(hdr) >= need:
                try:
                    vals = struct.unpack_from(fmt_full, hdr, 0)
                    if fmt.endswith("q"):
                        v1, v2, dv, n = float(vals[0]), float(vals[1]), float(vals[2]), int(vals[3])
                    else:
                        v1, v2, dv, n = float(vals[0]), float(vals[1]), float(vals[2]), int(vals[3])

                    if n > 0 and (len(dat) == n * 4 or len(dat) == n * 8):
                        wn = v1 + np.arange(n, dtype=np.float64) * dv
                        if len(dat) == n * 4:
                            vec = np.frombuffer(dat, dtype=np.dtype(endian + "f4")).astype(np.float64)
                        else:
                            vec = np.frombuffer(dat, dtype=np.dtype(endian + "f8"))

                        # Avoid duplicate boundary sample between panels
                        if wn_blocks and abs(wn[0] - wn_blocks[-1][-1]) <= max(1e-6, 1e-6 * abs(dv)):
                            wn = wn[1:]
                            vec = vec[1:]

                        if wn.size:
                            wn_blocks.append(wn)
                            val_blocks.append(vec)
                            v1_list.append(v1)
                            v2_list.append(v2)
                        i += 2
                        matched = True
                        break
                except Exception:
                    pass

        if not matched:
            i += 1

    if not wn_blocks:
        raise ValueError("No recognizable panels found in TAPE12 file.")

    wn = np.concatenate(wn_blocks)
    val = np.concatenate(val_blocks)

    return xr.Dataset(
        data_vars={var_name: ("wavenumber", val,  {"long_name": var_name, "units": units}),},
        coords={"wavenumber": ("wavenumber", wn)},
        attrs={
            "source": os.path.basename(path),
            "endianness": "little" if endian == "<" else "big",
            "record_marker_bytes": marker_bytes,
            "panel_count": len(val_blocks),
            "v1_first": v1_list[0],
            "v2_last": v2_list[-1],
        },
    )