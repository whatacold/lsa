#!/bin/bash

PY=python3

$PY -u lsw.py $PY test/echo.py <<EOF
HELLO WORLD, some text.
EOF

# relay output of subprocess
$PY -u lsw.py echo "hello world"