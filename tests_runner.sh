#!/bin/sh

PYTHON="python"

$PYTHON setup.py install

$PYTHON -m unittest discover tests/
