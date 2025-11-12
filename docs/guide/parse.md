# Parse Outputs (TAPE7/TAPE12 → xarray)

- **TAPE12**: returns `Dataset` with coordinate `wavenumber` and data vars like `optical_depth`, plus attrs (endianness, record markers, panels).
- **TAPE7**: metadata & integrals (e.g., PW). Document units and vertical coordinates.

### Dataset attributes (recommended)
- `source`: basename of TAPE file
- `endianness`: "little" | "big"
- `record_marker_bytes`: 4 | 8
- `panel_count`: int
- `v1_first` / `v2_last`: floats