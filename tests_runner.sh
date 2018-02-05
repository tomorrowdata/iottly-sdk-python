#!/bin/sh

PYTHON="python3"

$PYTHON setup.py install

$PYTHON -m unittest discover tests/
