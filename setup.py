from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="austin-python",
    version="0.1.0",
    description=("Python wrapper for Austin, the frame stack sampler for CPython"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/P403n1x87/austin-python",
    author="Gabriele N. Tornetta",
    author_email="phoenix1987@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GPLv3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="profiler stack sampler",
    packages=find_packages(exclude=["docs", "test"]),
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=["aiohttp", "psutil", "pyfiglet"],
    extras_require={"test": ["pytest-cov", "tox-travis", "coveralls"]},
    entry_points={"console_scripts": ["austin2ss=austin.format.speedscope:main"]},
    project_urls={  # TODO
        "Bug Reports": "https://github.com/P403n1x87/austin-python/issues",
        "Source": "https://github.com/P403n1x87/austin-python",
    },
)
