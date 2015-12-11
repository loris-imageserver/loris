#!/bin/bash
# Run all the tests

python -m unittest discover -s tests -p *_t.py
