#!/usr/bin/env python
# coding: utf-8

import subprocess
import select
import sys
import fcntl
import os
import logging
import platform
import argparse

SELECT_INTERVAL = 1

logging.basicConfig()
logger = logging.getLogger("lsa")

class LsOutputAdapter:
    def __init__(self, original_encoding='utf-8'):
        self.original_encoding = original_encoding

        self.state = 0 # 1: reading header, 2: reading body, 0: neither
        self.expected_len = 0 # larger than header keyword
        self.input_buffer = b''
        self.lsp_headers = b''
        self.lsp_body_length = 0
        self.lsp_body = b''

        self.output_buffer = b''

        self.CONTENT_LENGTH_KEY = b'Content-Length: '
        self.MIN_LEN = len(self.CONTENT_LENGTH_KEY)
        self.HEADER_SEPERATOR = b'\r\n'
        self.HEADERS_BODY_SEPERATOR = b'\r\n\r\n'

    def process_input(self, input):
        if not input:
            return
        logger.debug("state: {}, buffer: {}, input: {}".format(self.state, self.input_buffer, input))
        self.input_buffer = self.input_buffer + input
        self.process_input_buffer()
        return self.get_and_clear_output()

    def process_input_buffer(self):
        # if not self.input_buffer:
        #     return              # avoid infinite loop

        if 0 == self.state:
            if len(self.input_buffer) > self.MIN_LEN:
                self.state = 1
                self.process_input_buffer()
        elif 1 == self.state:
            cl_start = self.input_buffer.find(self.CONTENT_LENGTH_KEY)
            if -1 == cl_start:  # not found
                # XXX Part of `Content-Length: ` may be at the end
                keep_len = len(self.CONTENT_LENGTH_KEY) - 1
                flush_end = len(self.input_buffer) - keep_len
                self.output_buffer = self.output_buffer + self.input_buffer[:flush_end]
                self.input_buffer = self.input_buffer[flush_end:]
                self.state = 0
                return
            else:
                if cl_start > 0:
                    self.output_buffer = self.output_buffer + self.input_buffer[:cl_start]
                    self.input_buffer = self.input_buffer[cl_start:]
                    cl_start = 0
                ct_end = self.input_buffer.find(self.HEADER_SEPERATOR, cl_start)
                if ct_end == -1:  # incomplete header, keep reading
                    self.state = 1
                    return
                self.lsp_body_length = int(self.input_buffer[cl_start + len(self.CONTENT_LENGTH_KEY):ct_end])

                headers_end_pos = self.input_buffer.find(self.HEADERS_BODY_SEPERATOR)
                if -1 == headers_end_pos: # keep reading header
                    self.state = 1
                    return
                self.lsp_headers = self.input_buffer[(ct_end + len(self.HEADER_SEPERATOR)):(headers_end_pos + len(self.HEADER_SEPERATOR))]
                body_start = headers_end_pos + len(self.HEADERS_BODY_SEPERATOR)
                self.input_buffer = self.input_buffer[body_start:]
                self.state = 2
                self.process_input_buffer()
        elif 2 == self.state:
            if len(self.input_buffer) < self.lsp_body_length: # keep reading body
                return

            self.lsp_body = self.input_buffer[:self.lsp_body_length]
            self.input_buffer = self.input_buffer[self.lsp_body_length:]
            self.convert_lsp_message()
            self.lsp_body_length = 0
            self.lsp_headers = b''
            self.lsp_body = b''

            self.state = 0
            self.process_input_buffer()
            return

    def convert_lsp_message(self):
        try:
            unicode_str = self.lsp_body.decode(self.original_encoding, 'strict')
            if len(unicode_str) < self.lsp_body_length:  # there is non-ascii chars
                self.lsp_body = unicode_str.encode('utf-8')
                self.lsp_body_length = len(self.lsp_body)
        except UnicodeDecodeError:
            pass  # no conversion, keep it as is
        content_length = "Content-Length: {}\r\n".format(self.lsp_body_length) \
                                                 .encode(encoding='utf8')
        self.output_buffer = self.output_buffer + content_length + self.lsp_headers + \
            self.HEADER_SEPERATOR + self.lsp_body

        self.lsp_headers = b''
        self.lsp_body = b''

    def get_and_clear_output(self):
        output = self.output_buffer
        self.output_buffer = b''
        return output

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
        logger.debug("read from stdin: %s", input)
        lsproc_stdin.write(input)
        lsproc_stdin.flush()

def handle_lsproc_stderr(lsproc_stderr, sys_stderr):
    input = read_greedly(lsproc_stderr)
    if input:
        logger.debug("read from lsproc stderr: %s", input)
        sys_stderr.write(input)
        sys_stderr.flush()

def handle_lsproc_stdout(lsproc_stdout, adapter, sys_stdout):
    input = read_greedly(lsproc_stdout)
    if input:
        logger.debug("read from lsproc stdout: %s", input)
        output = adapter.process_input(input)
        sys_stdout.write(output)
        sys_stdout.flush()

def set_fd_nonblock(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL);
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def main():
    arg_parser = argparse.ArgumentParser(description='A Language Server Adapter',
                                         epilog='''
                                         Examples:
                                         1. --original_output_encoding -- clangd --foo --bar
                                         2. clangd
                                         ''')
    arg_parser.add_argument("--original-output-encoding",
                            default="utf-8",
                            help="The original output encoding the adapted LS used")
    arg_parser.add_argument("--log-level",
                            choices=['DEBUG', 'INFO'],
                            default="DEBUG",
                            help="The log level")
    arg_parser.add_argument("server",
                            help="The adapted language server")
    arg_parser.add_argument("option",
                            nargs="*",
                            help="The options for the adapted language server")
    args = arg_parser.parse_args()

    log_levels_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
    }
    logger.setLevel(log_levels_map[args.log_level])

    lsproc_args = [args.server] + args.option
    lsproc = subprocess.Popen(lsproc_args,
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

    adapter = LsOutputAdapter(args.original_output_encoding)

    while True:
        rc = lsproc.poll()
        if rc is not None:
            logger.info("ls proc terminated with rc: %d", rc)
            break

        readable, _, _ = select.select([sys_stdin, lsproc_stdout, lsproc_stderr],
                                            [], [], SELECT_INTERVAL)
        if lsproc_stdout in readable:
            handle_lsproc_stdout(lsproc_stdout, adapter, sys_stdout)
        if lsproc_stderr in readable:
            handle_lsproc_stderr(lsproc_stderr, sys_stderr)
        if sys_stdin in readable:
            handle_stdin(sys_stdin, lsproc_stdin)

    # lsproc.terminate()

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logger.info("py version: %s, cwd: %s",
                platform.python_version(),
                os.getcwd())
    main()