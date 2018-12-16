#!/bin/bash

PY=python3

$PY lsa_unittest.py

$PY ../lsa.py $PY echo.py <<EOF
HELLO WORLD, some text.
EOF

# relay output of subprocess
$PY ../lsa.py echo "hello world"

$PY ../lsa.py $PY ls.py utf-8
$PY ../lsa.py --original-response-encoding gbk -- $PY ls.py gbk