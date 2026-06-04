"""
SignalPulse-CLI - Setup configuration for pip installation.
"""

from setuptools import setup, find_packages

# Read long description from README
here = __file__
try:
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "SignalPulse-CLI: Lightweight terminal-based cross-platform social signal aggregation and AI-powered briefing engine."

# Read requirements
try:
    with open("requirements.txt", encoding="utf-8") as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]
except FileNotFoundError:
    requirements = ["requests>=2.28.0", "rich>=13.0.0"]

setup(
    name="signalpulse-cli",
    version="1.0.0",
    description="Lightweight terminal-based cross-platform social signal aggregation and AI-powered briefing engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="SignalPulse Team",
    python_requires=">=3.9",
    packages=find_packages(exclude=["tests*", "docs*"]),
    install_requires=requirements,
    extras_require={
        "yaml": ["pyyaml>=6.0"],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "mypy>=1.0",
            "black>=23.0",
            "isort>=5.0",
            "flake8>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "signalpulse=signalpulse_cli.__main__:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Utilities",
    ],
)
