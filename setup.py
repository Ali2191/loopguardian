#!/usr/bin/env python3
"""
Setup script for LoopGuard - Real-time AI coding agent loop detector
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read the contents of LICENSE file
with open("LICENSE", "r", encoding="utf-8") as fh:
    license_text = fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="loopguardian",
    version="0.1.1",
    author="LoopGuard Team",
    author_email="team@loopguard.dev",
    maintainer="LoopGuard Team",
    maintainer_email="team@loopguard.dev",
    description="Real-time AI coding agent loop detector for Claude Code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/loopguard/loopguard",
    project_urls={
        "Bug Tracker": "https://github.com/loopguard/loopguard/issues",
        "Documentation": "https://loopguard.readthedocs.io/",
        "Source Code": "https://github.com/loopguard/loopguard",
        "Changelog": "https://github.com/loopguard/loopguard/blob/main/CHANGELOG.md",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    package_data={
        "loopguard": [
            "data/*.json",
            "data/*.yaml",
            "templates/*.plist",
            "scripts/*.sh",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Debuggers",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocstrings>=0.23.0",
            "mkdocs-gen-files>=0.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "loopguardian=loopguard.cli:main",
            "loopguardian-monitor=loopguard.monitor:main",
            "loopguardian-config=loopguard.config:main",
        ],
    },
    zip_safe=False,
    keywords="claude code monitoring loop detection debugging ai assistant",
    platforms=["MacOS X", "Linux"],
    license="MIT",
)
