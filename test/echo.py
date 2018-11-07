#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

input = sys.stdin.readline()
sys.stdout.write(input)
sys.stderr.write("Also echoed in stderr: " + input)