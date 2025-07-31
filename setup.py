#!/usr/bin/env python3
"""
Setup script for modbusapi package
"""

from setuptools import setup, find_packages

setup(
    name="modbusapi",
    version="0.1.0",
    description="Unified API for Modbus communication",
    author="VeriDock Team",
    author_email="info@veridock.com",
    packages=find_packages(),
    install_requires=[
        "pymodbus>=3.0.0",
        "python-dotenv>=0.19.0",
        "flask>=2.0.0",
        "paho-mqtt>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
        ],
        "rest": [
            "flask>=2.0.0",
        ],
        "mqtt": [
            "paho-mqtt>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "modbusapi=modbusapi.shell:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
)
