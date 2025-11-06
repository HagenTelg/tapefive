# tapefive
(under construction, not ready for action) A high-level Python API for LBLRTM: build and validate TAPE5, run LNFL/LBLRTM, and parse outputs with clear errors.

# Disclamer ... what it can do so far
nothing

# Introduction
This library provides a high-level Python API for configuring and running the line-by-line radiative transfer workflow with LNFL and LBLRTM. It replaces manual TAPE5 editing with schema-validated builders, catches common input mistakes early, and surfaces actionable error messages.

Under the hood it wraps the LNFL/LBLRTM executables, manages run directories, and parses their outputs into ergonomic Python objects—typically xarray Datasets/DataArrays with coordinates, attributes, and provenance. LNFL/LBLRTM must be installed separately; this package focuses on safe configuration, execution, and result handling.
