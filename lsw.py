#!/usr/bin/env python
# coding: utf-8

# only python 2.7 is supported right now, due to python 3's stdin/stdout/stderr not in binary mode

import subprocess
import select
import sys
import fcntl
import os
import logging
import platform

SELECT_INTERVAL = 1

logging.basicConfig()
logger = logging.getLogger("lsw")
logger.setLevel(logging.DEBUG)

def read_greedly(fd):
    input = b""
    while True:
        try:
            this_read = fd.read(1024)
            if this_read:
                # why python 2 and 3 diffs at `-u` command line option?
                input = input + this_read
            else:
                break # EOF
        except IOError:
            break
    return input

def handle_stdin(stdin, lsproc_stdin):
    input = read_greedly(stdin)
    if input:
        logger.debug("read input from stdin: %s", input)
        # TODO handle exit
        lsproc_stdin.write(input)
        lsproc_stdin.flush()

def handle_lsproc_stderr(lsproc_stderr, sys_stderr):
    input = read_greedly(lsproc_stderr)
    if input:
        logger.debug("read input from lsproc stderr: %s", input)
        sys_stderr.write(input)
        sys_stderr.flush()

def handle_lsproc_stdout(lsproc_stdout, sys_stdout):
    input = read_greedly(lsproc_stdout)
    if input:
        logger.debug("read input from lsproc stdout: %s", input)
        sys_stdout.write(input)
        sys_stdout.flush()

def set_fd_nonblock(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL);
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def main():
    lsproc = subprocess.Popen(sys.argv[1:],
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)

    lsproc_stdin = os.fdopen(lsproc.stdin.fileno(), 'wb')
    lsproc_stdout = os.fdopen(lsproc.stdout.fileno(), 'rb')
    lsproc_stderr = os.fdopen(lsproc.stderr.fileno(), 'rb')

    sys_stdin = os.fdopen(sys.stdin.fileno(), "rb")
    sys_stdout = os.fdopen(sys.stdout.fileno(), "wb")
    sys_stderr = os.fdopen(sys.stderr.fileno(), "wb")

    set_fd_nonblock(lsproc_stdout)
    set_fd_nonblock(lsproc_stderr)
    set_fd_nonblock(sys_stdin)

    while True:
        rc = lsproc.poll()
        if rc is not None:
            logger.info("ls proc terminated with rc: %d", rc)
            break

        readable, _, _ = select.select([sys_stdin, lsproc_stdout, lsproc_stderr],
                                            [], [], SELECT_INTERVAL)
        if lsproc_stdout in readable:
            handle_lsproc_stdout(lsproc_stdout, sys_stdout)
        if lsproc_stderr in readable:
            handle_lsproc_stderr(lsproc_stderr, sys_stderr)
        if sys_stdin in readable:
            handle_stdin(sys_stdin, lsproc_stdin)

    # lsproc.terminate()

if __name__ == "__main__":
    logger.info("py version: %s, cwd: %s",
                platform.python_version(),
                os.getcwd())
    main()