"""Setup configuration for Tenga Inventory POS."""
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="tenga-inventory",
    version="0.1.0",
    description="Tenga Inventory Point-of-Sale System",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.9",
)
