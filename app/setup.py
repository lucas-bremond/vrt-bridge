# MIT License

import os
import pathlib

from setuptools import setup, find_namespace_packages

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="vrt-bridge",
    use_scm_version={
        "root": "..",
    },
    packages=find_namespace_packages(),
    package_data={"vrt_bridge": ["py.typed"]},
    include_package_data=True,
    license="MIT License",
    description="Convert a raw I/Q stream into VRT (VITA-49) packets.",
    long_description=(
        pathlib.Path(__file__).absolute().parent.parent / "README.md"
    ).read_text(encoding="utf-8"),
    author="Lucas Brémond",
    author_email="lucas.bremond@gmail.com",
    classifiers=[
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    setup_requires=[
        "setuptools-scm~=7.0",
    ],
    install_requires=[
        "click~=8.1",
        "pyyaml~=6.0",
        "aioprocessing~=2.0",
        "numpy~=1.24",
        "scipy~=1.10",
    ],
    entry_points={
        "console_scripts": [
            "vrt-bridge = vrt_bridge.cli:cli",
        ],
    },
)
