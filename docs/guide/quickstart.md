# Quickstart

```python
import xarray as xr
# from tapefive.tape5 import Tape5   # when ready
# from tapefive.run import run_lnfl, run_lblrtm
# from tapefive.parse import read_tape12

# 1) Build a tiny spectral window TAPE5 (placeholder for now)
# t5 = Tape5(v1=10280.0, v2=11010.0, dv=0.5, atmosphere="MLS", molecules=["H2O"])

# 2) Run external tools (assumes lnfl/lblrtm on PATH)
# run_lnfl(t5)
# ds = run_lblrtm(t5)

# 3) Parse outputs to xarray (e.g., TAPE12)
# ds = read_tape12("path/to/TAPE12")

# For docs demonstration, show expected schema:
print(xr.Dataset(
    data_vars={"optical_depth": (("wavenumber",), [])},
    coords={"wavenumber": (("wavenumber",), [])},
    attrs={"provenance": "Created by tapefive"}
))
```