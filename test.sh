#!/usr/bin/env bash

# assume modern unittest and python 2.7 + nose

#python -m unittest discover -s `dirname "$0"` -p '*_test.py'

nosetests -v -s \
    --with-coverage --with-doctest --cover-erase \
    --doctest-options='+ELLIPSIS,+NORMALIZE_WHITESPACE' \
    --cover-package=panobbgo --cover-package=panobbgo_lib

exit $?
