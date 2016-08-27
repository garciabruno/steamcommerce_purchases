#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='steamcommerce_purchases',
    version='0.0.1',
    description='Library to handle purchases throught the Steam store',
    author='[NIN]',
    author_email='admin@extremegaming-arg.com.ar',
    keywords='steamcommerce_purchases',
    packages=find_packages(),
    install_requires=['requests', 'steam', 'steam[client]']
)
