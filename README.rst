mediti-collector
================
.. image:: https://travis-ci.com/mristin/mediti-collector.svg?branch=master
    :target: https://travis-ci.com/mristin/mediti-collector
    :alt: Build Status

.. image:: https://coveralls.io/repos/github/mristin/mediti-collector/badge.svg?branch=master
    :target: https://coveralls.io/github/mristin/mediti-collector?branch=master
    :alt: Coverage

.. image:: https://badges.frapsoft.com/os/mit/mit.png?v=103
    :target: https://opensource.org/licenses/mit-license.php
    :alt: MIT License

.. image:: https://badge.fury.io/py/mediti-collector.svg
    :target: https://badge.fury.io/py/mediti-collector
    :alt: PyPI - version

.. image:: https://img.shields.io/pypi/pyversions/mediti-collector.svg
    :alt: PyPI - Python Version

Mediti-collector collects training data for
`mediti <https://github.com/mristin/mediti>`_.

The actions are recorded *via* the web camera after being announced by
a robotic text-to-speech voice.

The user interface is based on OpenCV 4, while we used pyttsx3 to access
the operating system's text-to-speech generator.

Usage
=====
Simple
------
You need to specify the identifier for the recorded sequence as well as
an output directory:

.. code-block:: bash

    mediti-collector \
        --outdir /some/path \
        --identifier some-sequence

The output directory will be created if it doesn't exist. The sequence
identifier can only contain letters, numbers, a dash or an underscore.

Full Description
----------------
Here is a full description of the command-line arguments.

.. code-block:: bash

    mediti-collector
        [-h] -o OUTDIR -i IDENTIFIER [-f FREQUENCY]
        [--period PERIOD] [--camera CAMERA]
        [--actions ACTIONS [ACTIONS ...]]

``-h, --help``
    show the help message and exit

``-o OUTDIR, --outdir OUTDIR``
    path to the directory where sequence will be recorded;
    if it does not exist, it will be created.

``-i IDENTIFIER, --identifier IDENTIFIER``
    identifier of the recorded sequence

``-f FREQUENCY, --frequency FREQUENCY``
    frequency at which to take the images, in Hz (default: 1.0)

``--period PERIOD``
    period of a single action, in seconds (default: 7.0)

``--camera CAMERA``
    Camera identifier (default: 0)

``--actions ACTION [ACTION ...]``
    list of actions to record (duplicates skew the distribution)
    (default: attending, unattending, meditating)

Screenshots
-----------
.. image:: https://media.githubusercontent.com/media/mristin/mediti-collector/master/screenshots/screenshot-attending.png

.. image:: https://media.githubusercontent.com/media/mristin/mediti-collector/master/screenshots/screenshot-unattending.png

.. image:: https://media.githubusercontent.com/media/mristin/mediti-collector/master/screenshots/screenshot-meditating.png

Installation
============
We provide a prepackaged PEX file that can be readily downloaded and executed.
Please see the `Releases section <https://github.com/mristin/mediti-collector/releases>`_.

Alternatively, you can install mediti-collector with pip in an virtual
environment:

.. code-block:: bash

    pip3 install mediti-collector

Contributing
============
We are very grateful for and welcome contributions: be it opening of the issues,
discussing future features or submitting pull requests.

To submit a pull request:

* Check out the repository.
* In the repository root, create the virtual environment:

.. code-block:: bash

    python3 -m venv venv3

* Activate the virtual environment:

.. code-block:: bash

    source venv3/bin/activate

* Install the development dependencies:

.. code-block:: bash

    pip3 install -e .[dev]

* Implement your changes.
* Run precommit.py to execute pre-commit checks locally.

Versioning
==========
We follow `Semantic Versioning <http://semver.org/spec/v1.0.0.html>`_. The version X.Y.Z indicates:

* X is the major version (backward-incompatible),
* Y is the minor version (backward-compatible), and
* Z is the patch version (backward-compatible bug fix).
