#!/bin/bash

PY=python3

$PY lsa.py $PY test/echo.py <<EOF
HELLO WORLD, some text.
EOF

# relay output of subprocess
$PY lsa.py echo "hello world"

$PY lsa.py $PY test/ls.py utf-8
$PY lsa.py --original-response-encoding gbk -- $PY test/ls.py gbk