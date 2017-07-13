#!/bin/bash

# Figure out where we live
BUILD_DIR="$(dirname $(realpath $0))"
BUILD_LOG="${BUILD_DIR}/build.log"

# Move into the right directory
pushd "${BUILD_DIR}" >> "${BUILD_LOG}" 2>&1

# Clean up first
if [[ -e 'dist' ]]; then
    rm -rf dist
fi

if [[ -e "${BUILD_LOG}" ]]; then
    rm -f "${BUILD_LOG}"
fi

python setup.py sdist >> "${BUILD_LOG}" 2>&1
SDIST_RESULT="${?}"

python setup.py bdist_wheel --universal >> "${BUILD_LOG}" 2>&1
BDIST_RESULT="${?}"

if [[ ${SDIST_RESULT} -eq 0 ]] && [[ ${BDIST_RESULT} -eq 0 ]]; then
    pip install -U dist/cfw*.whl >> "${BUILD_LOG}" 2>&1
    popd >> /dev/null 2>&1

    # All good here so return a zero status
    exit 0
fi

# Looks like we had a build failure so we'll output the build log here
cat "${BUILD_LOG}"
popd >> /dev/null 2>&1

# Exit with a non-zero status so anything dependant can fail fast
exit 1
