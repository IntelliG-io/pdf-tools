"""
Setup script for PDF Splitter CLI.

This script configures the package for installation via pip.
Supports both development and production installations.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="pdf-splitter-cli",
    version="1.0.0",
    description="Comprehensive CLI tool for splitting PDF files with batch processing and metadata preservation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="PDF Splitter CLI Contributors",
    author_email="",
    url="https://github.com/yourusername/pdf-splitter-cli",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/pdf-splitter-cli/issues",
        "Source": "https://github.com/yourusername/pdf-splitter-cli",
        "Documentation": "https://github.com/yourusername/pdf-splitter-cli#readme",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "pypdf>=3.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pdf-splitter=pdf_splitter.cli:cli",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "Topic :: Office/Business",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    keywords="pdf split splitter cli batch metadata pages ranges chunks extract",
    license="MIT",
    include_package_data=True,
    zip_safe=False,
)
