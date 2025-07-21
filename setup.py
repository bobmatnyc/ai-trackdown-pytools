#!/usr/bin/env python
"""Setup script for ai-trackdown-pytools.

This file is included for compatibility with older pip versions.
The actual package configuration is in pyproject.toml.
"""

from setuptools import setup

# Read the README for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Minimal setup() call - most configuration is in pyproject.toml
setup(
    long_description=long_description,
    long_description_content_type="text/markdown",
)