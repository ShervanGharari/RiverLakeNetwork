# Environment Setup for RiverLakeNetwork

This folder contains scripts to create and manage the Python virtual environment
for the RiverLakeNetwork project.

The setup is designed to be flexible:
- By default, it installs **core dependencies** and the optional `plot` dependencies.
- **Jupyter installation and kernel registration is optional**.

---

## Files

- **`CreateRiverLakeEnv.sh`**: Bash script to:
  1. Create a Python virtual environment (`venv`)
  2. Install project dependencies from the parent `pyproject.toml`
     - Core dependencies: `numpy`, `pandas`, `geopandas`, `shapely`, `networkx`, `pyyaml`
     - Optional extra `plot`: `matplotlib`
  3. Optionally install Jupyter and register a kernel
     - Controlled by the `JUPYTER_ACTIVE` variable
     - Default is `true`

---

## Configuration Variables

| Variable         | Default | Description |
|-----------------|---------|-------------|
| `VENV_NAME`      | `RiverLakeEnv` | Name of the virtual environment folder to create |
| `VENV_PATH`      | `./RiverLakeEnv` | Full path to the virtual environment. <br> Defaults to the current folder if not provided. Can be overridden by exporting `VENV_PATH` before running the script. |
| `KERNEL_NAME`    | `RiverLakeEnv` | Name of the Jupyter kernel to register if Jupyter is enabled |
| `JUPYTER_ACTIVE` | `true` | Controls whether Jupyter and the kernel are installed. <br> Set to `false` to skip Jupyter installation. Can also be overridden by uncommenting inside the script. |



**Example**: with Jupyter installation:

```bash
bash CreateRiverLakeEnv.sh
```

**Example**: disable Jupyter installation:

```bash
JUPYTER_ACTIVE=false bash CreateRiverLakeEnv.sh
```

**Example**: defined location for installed env:

```bash
VENV_PATH="../RiverLakeEnv" bash CreateRiverLakeEnv.sh # or can be VENV_PATH="path_to_there/RiverLakeEnv"
```