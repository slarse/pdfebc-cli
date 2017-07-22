# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

test_requirements = ['pytest>=3.1.1', 'pytest-cov>=2.5.1', 'codecov']
required = []

setup(
    name='pdfebc-cli',
    version='0.0.1',
    description=('A command line utility for the pdfebc tools.'),
    long_description=readme,
    author='Simon Larsén',
    author_email='slarse@kth.se',
    url='https://github.com/slarse/pdfebc-cli',
    #download_url='https://github.com/slarse/{cookiecutter.project_name}/archive/v0.1.0.tar.gz',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    tests_require=test_requirements,
    install_requires=required,
    scripts=['bin/pdfebc-cli'],
    include_package_data=True,
    zip_safe=False
)
