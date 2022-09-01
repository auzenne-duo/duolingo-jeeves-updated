#!/bin/bash
set -ex

WORKSPACE=${WORKSPACE:-$(pwd)}
PYENV_HOME="$WORKSPACE/.pyenv/"
python3 -m venv "$PYENV_HOME"
. "$PYENV_HOME/bin/activate"
export PYTHONPATH="$WORKSPACE"

pip install -U pip wheel setuptools
pip install -r dev-requirements.txt

python jeeves/scripts/force_refresh.py
