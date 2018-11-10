#!/bin/bash

PY=python3

$PY lsw.py $PY test/echo.py <<EOF
HELLO WORLD, some text.
EOF

# relay output of subprocess
$PY lsw.py echo "hello world"

$PY lsw.py $PY test/ls.py utf-8
$PY lsw.py --original-output-encoding gbk -- $PY test/ls.py gbk