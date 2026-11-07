# Keep NCAR's version pins out of install_requires

## Why

`install_requires` capped every dependency, and included tools mom6_forge never imports: jupyterlab, sphinx, black and pytest. Anyone installing mom6_forge into another environment inherited NCAR's JupyterHub pins (matplotlib < 3.10 from #95) and these tool versions. On NCI, dropping the jupyter requirement is what let the environment resolve.

## What

- `install_requires` lists only what mom6_forge imports at runtime (numpy, xarray, scipy, matplotlib, netCDF4, dask, cartopy, cf_xarray, xesmf, regionmask, gitpython, ipywidgets, ipympl), with lower bounds only. The lower bounds are unchanged.
- The tools are extras: `notebook` (jupyterlab), `docs` (sphinx, the theme, nbsphinx, myst-parser) and `dev` (black, pytest, pytest-cov). setuptools is left to `[build-system]`.
- `environment.yml`, which CI and NCAR's environment build from, installs `-e ./[dev,docs,notebook]` and keeps every previous pin. NCAR's environment resolves to the same versions as before.

## Checks

- In the dev environment, `pip install --dry-run -e '.[dev,docs,notebook]'` resolves with nothing new. A plain `-e .` no longer asks for jupyterlab, sphinx, black or pytest.

## Downstream

CrocoDash's and crocontainer's `environment.yml` install mom6_forge with `-e …/mom6_forge/` and got black and sphinx_rtd_theme through it. When their visualCaseGen/mom6_forge pins move past this, they should list black themselves (CrocoDash formats with it), or install `…/mom6_forge/[dev]`.

Closes #124

🤖 Generated with [Claude Code](https://claude.com/claude-code)
