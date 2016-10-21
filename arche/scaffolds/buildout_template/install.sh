#!/bin/bash
virtualenv .
bin/python bootstrap-buildout.py
bin/buildout
