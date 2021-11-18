name: Build Wheel

on:
  push:
    tags:
      - '*'

jobs:
  build_wheel:
    runs-on: ubuntu-latest
    env:
      TWINE_USERNAME: __token__
      TWINE_PASSWORD: ${{ secrets.TWINE_TOKEN }}

    steps:
    - name: Set up Python 3.8
      uses: actions/setup-python@v2
      with:
        python-version: 3.8

    - name: clone ocs
      uses: actions/checkout@v2

    - name: install build dependencies
      run: |
        python3 -m pip install --upgrade build twine

    - name: build wheel
      run: |
        python3 -m build

    - name: upload to test PyPI
      run: |
        python3 -m twine upload --repository testpypi dist/*
