"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
import os

from setuptools import setup, find_packages

import mediti_collector_meta

# pylint: disable=redefined-builtin

here = os.path.abspath(os.path.dirname(__file__))  # pylint: disable=invalid-name

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()  # pylint: disable=invalid-name

with open(os.path.join(here, 'requirements.txt'), encoding='utf-8') as fid:
    install_requires = [
        line for line in fid.read().splitlines() if line.strip()
    ]

setup(
    name=mediti_collector_meta.__title__,
    version=mediti_collector_meta.__version__,
    description=mediti_collector_meta.__description__,
    long_description=long_description,
    url=mediti_collector_meta.__url__,
    author=mediti_collector_meta.__author__,
    author_email=mediti_collector_meta.__author_email__,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    license='License :: OSI Approved :: MIT License',
    keywords='collect training data mediti',
    packages=find_packages(exclude=['doc', 'tests']),
    install_requires=install_requires,
    extras_require={
        # yapf: disable
        'dev': [
            'coverage>=4.5.1,<5',
            'pydocstyle>=3.0.0,<4',
            'mypy==0.730',
            'pylint==2.4.1',
            'yapf==0.27.0',
            'temppathlib>=1.0.3,<2',
            'isort>=4.3.21,<5',
            'twine>=1.12.1,<2',
        ],
        # yapf: enable
    },
    py_modules=['mediti_collector', 'mediti_collector_meta'],
    scripts=['bin/mediti-collector'],
    package_data={"mediti_collector": ["py.typed"]})
