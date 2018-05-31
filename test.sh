#!/usr/bin/env bash

if [[ ! -e "dmypy.sock" ]]; then
    dmypy start -- --disallow-untyped-calls --disallow-untyped-defs --ignore-missing-imports\
        --follow-imports=error --strict
fi

if ! dmypy check cfw; then
    exit 1
fi

PYTHONPATH="./" python cfw/testapp/test.py $@
