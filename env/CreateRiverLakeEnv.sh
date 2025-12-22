#!/usr/bin/env bash
set -e

# --------------------------
# Configuration
# --------------------------
VENV_NAME="RiverLakeEnv"
KERNEL_NAME="RiverLakeEnv"
JUPYTER_ACTIVE=${JUPYTER_ACTIVE:-true}  # default true
# Uncomment to force disable Jupyter inside the script
# JUPYTER_ACTIVE=false
# Full path to virtual environment, default is current folder if not overridden
VENV_PATH="${VENV_PATH:-$(pwd)/$VENV_NAME}"
# Where the RiverLakeNetwork pyproject.toml is located (parent folder)
PROJECT_ROOT="$(dirname "$(dirname "$(realpath "$0")")")"

echo "----------------------------------------------------"
echo "Project root: $PROJECT_ROOT"
echo "Virtual environment name: $VENV_NAME"
echo "Virtual environment path: $VENV_PATH"
echo "Jupyter active: $JUPYTER_ACTIVE"
echo "----------------------------------------------------"

# --------------------------
# Remove old virtual environment
# --------------------------
if [ -d "$VENV_PATH" ]; then
    rm -rf "$VENV_PATH"
    echo "Removed existing virtual environment: $VENV_PATH"
fi

# --------------------------
# Remove old Jupyter kernel
# --------------------------
if [ "$JUPYTER_ACTIVE" = true ]; then
    if jupyter kernelspec list 2>/dev/null | grep -qw "$KERNEL_NAME"; then
        jupyter kernelspec remove -f "$KERNEL_NAME"
        echo "Removed existing Jupyter kernel: $KERNEL_NAME"
    fi
fi

# --------------------------
# Create new virtual environment
# --------------------------
python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"

# --------------------------
# Upgrade pip and build tools
# --------------------------
python3 -m pip install --upgrade pip setuptools wheel

# --------------------------
# Install package from pyproject.toml
# --------------------------
# Install core package + plot extra
python3 -m pip install -e "$PROJECT_ROOT[plot]"

# Install Jupyter and ipykernel if enabled
if [ "$JUPYTER_ACTIVE" = true ]; then
    python3 -m pip install jupyter ipykernel
fi

# --------------------------
# Register Jupyter kernel (if enabled)
# --------------------------
if [ "$JUPYTER_ACTIVE" = true ]; then
    if python3 -c "import ipykernel" &>/dev/null; then
        python3 -m ipykernel install \
            --name "$KERNEL_NAME" \
            --display-name "Python ($KERNEL_NAME)" \
            --user
        echo "Jupyter kernel '$KERNEL_NAME' installed."
    else
        echo "ipykernel not installed; skipping kernel registration."
    fi
fi

# --------------------------
# List kernels (optional)
# --------------------------
if [ "$JUPYTER_ACTIVE" = true ]; then
    jupyter kernelspec list
fi


if [ "$JUPYTER_ACTIVE" = true ]; then
    echo " Jupyter support is ENABLED."
    echo ""
    echo " You can now:"
    echo " 1) Run Python scripts directly, for example:"
    echo "    python run_river_network.py"
    echo ""
    echo " 2) Start Jupyter Notebook or Jupyter Lab:"
    echo "    jupyter notebook"
    echo "    # or"
    echo "    jupyter lab"
    echo ""
    echo " Then select the kernel:"
    echo "   Python ($KERNEL_NAME)"
    echo " OR "
    echo " You can run Python scripts directly using:"
    echo "   python run_river_network.py"
    echo ""
    echo " If you later need Jupyter, you can install it manually:"
    echo "   source $VENV_PATH/bin/activate"
    echo "   python -m pip install jupyter ipykernel"
    echo "   python -m ipykernel install --name \"$KERNEL_NAME\" \\"
    echo "       --display-name \"Python ($KERNEL_NAME)\" --user"
else
    echo " Jupyter support is DISABLED."
    echo ""
    echo " You can run Python scripts directly using:"
    echo "   python run_river_network.py"
    echo ""
    echo " If you later need Jupyter, you can install it manually:"
    echo "   source $VENV_PATH/bin/activate"
    echo "   python -m pip install jupyter ipykernel"
    echo "   python -m ipykernel install --name \"$KERNEL_NAME\" \\"
    echo "       --display-name \"Python ($KERNEL_NAME)\" --user"
fi

echo ""
echo "----------------------------------------------------"
