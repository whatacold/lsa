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
from enum import Enum

SELECT_INTERVAL = 1

logging.basicConfig()
logger = logging.getLogger("lsa")

class LsResponseAdapter:
    """Language server response adapter."""

    class State(Enum):
        INITIAL = 1
        READING_HEADER = 2
        READING_BODY = 3

    def __init__(self, original_encoding='utf-8'):
        self.__original_encoding = original_encoding

        self.__state = self.State.INITIAL
        self.__original_buffer = b''
        self.__adapted_buffer = b''

        self.__lsp_headers = b''
        self.__lsp_body_length = 0
        self.__lsp_body = b''

        self.CONTENT_LENGTH_KEY = b'Content-Length: '
        self.MIN_LEN_TO_ADAPT = len(self.CONTENT_LENGTH_KEY)
        self.HEADER_SEPERATOR = b'\r\n'
        self.HEADERS_BODY_SEPERATOR = b'\r\n\r\n'

    def adapt_response(self, response):
        """
        Adapt LSP response.

        The response may be partial.
        """
        if not response:
            return
        logger.debug("state: {}, buffer: {}, response: {}".format(self.__state,
                                                                  self.__original_buffer,
                                                                  response))
        self.__original_buffer = self.__original_buffer + response
        self.__adapt_original_buffer()
        return self.__get_and_clear_adapted_buffer()

    def __adapt_original_buffer(self):
        """Adapt original response that buffered"""
        # if not self.__original_buffer:
        #     return              # avoid infinite loop

        if self.State.INITIAL == self.__state:
            if len(self.__original_buffer) > self.MIN_LEN_TO_ADAPT:
                self.__state = self.State.READING_HEADER
                self.__adapt_original_buffer()
        elif self.State.READING_HEADER == self.__state:
            cl_start = self.__original_buffer.find(self.CONTENT_LENGTH_KEY)
            if -1 == cl_start:  # not found
                # `Content-Length: ` part may be at the end
                keep_len = len(self.CONTENT_LENGTH_KEY) - 1
                flush_end = len(self.__original_buffer) - keep_len
                self.__adapted_buffer = self.__adapted_buffer + self.__original_buffer[:flush_end]
                self.__original_buffer = self.__original_buffer[flush_end:]
                self.__state = self.State.INITIAL
                return
            else:
                if cl_start > 0:
                    self.__adapted_buffer = self.__adapted_buffer + self.__original_buffer[:cl_start]
                    self.__original_buffer = self.__original_buffer[cl_start:]
                    cl_start = 0
                ct_end = self.__original_buffer.find(self.HEADER_SEPERATOR, cl_start)
                if ct_end == -1:  # incomplete header, keep reading
                    self.__state = self.State.READING_HEADER
                    return
                self.__lsp_body_length = int(self.__original_buffer[cl_start +
                                                                len(self.CONTENT_LENGTH_KEY):ct_end])

                headers_end_pos = self.__original_buffer.find(self.HEADERS_BODY_SEPERATOR)
                if -1 == headers_end_pos: # keep reading header
                    self.__state = self.State.READING_HEADER
                    return
                self.__lsp_headers = self.__original_buffer[(ct_end + len(self.HEADER_SEPERATOR)) :
                                                        (headers_end_pos + len(self.HEADER_SEPERATOR))]
                body_start = headers_end_pos + len(self.HEADERS_BODY_SEPERATOR)
                self.__original_buffer = self.__original_buffer[body_start:]
                self.__state = self.State.READING_BODY
                self.__adapt_original_buffer()
        elif self.State.READING_BODY == self.__state:
            if len(self.__original_buffer) < self.__lsp_body_length: # keep reading body
                return

            self.__lsp_body = self.__original_buffer[:self.__lsp_body_length]
            self.__original_buffer = self.__original_buffer[self.__lsp_body_length:]
            self.__convert_message_to_utf8()
            self.__lsp_body_length = 0
            self.__lsp_headers = b''
            self.__lsp_body = b''

            self.__state = self.State.INITIAL
            self.__adapt_original_buffer()
            return

    def __convert_message_to_utf8(self):
        """Convert LSP message to UTF-8 when necessary."""
        try:
            unicode_str = self.__lsp_body.decode(self.__original_encoding, 'strict')
            if len(unicode_str) < self.__lsp_body_length:
                self.__lsp_body = unicode_str.encode('utf-8')
                self.__lsp_body_length = len(self.__lsp_body)
        except UnicodeDecodeError:
            pass  # no conversion, keep it as is
        content_length = "Content-Length: {}\r\n".format(self.__lsp_body_length) \
                                                 .encode(encoding='utf8')
        self.__adapted_buffer = self.__adapted_buffer + content_length + self.__lsp_headers + \
            self.HEADER_SEPERATOR + self.__lsp_body

        self.__lsp_headers = b''
        self.__lsp_body = b''

    def __get_and_clear_adapted_buffer(self):
        """Return adapted buffer and clear it."""
        output = self.__adapted_buffer
        self.__adapted_buffer = b''
        return output

def read_greedily(fd):
    """Read data from fd as much as possible."""
    input = b""
    while True:
        try:
            this_read = fd.read(1024)
            if this_read:
                input = input + this_read
            else:
                break # EOF
        except IOError:
            break
    return input

def handle_stdin(stdin, lsproc_stdin):
    """Handle the stdin."""
    input = read_greedily(stdin)
    if input:
        logger.debug("read from stdin: %s", input)
        lsproc_stdin.write(input)
        lsproc_stdin.flush()

def handle_lsproc_stderr(lsproc_stderr, sys_stderr):
    """Handle the stderr from a language server."""
    input = read_greedily(lsproc_stderr)
    if input:
        logger.debug("read from lsproc stderr: %s", input)
        sys_stderr.write(input)
        sys_stderr.flush()

def handle_lsproc_stdout(lsproc_stdout, adapter, sys_stdout):
    """Handle the output from a language server."""
    input = read_greedily(lsproc_stdout)
    if input:
        logger.debug("read from lsproc stdout: %s", input)
        output = adapter.adapt_response(input)
        sys_stdout.write(output)
        sys_stdout.flush()

def set_fd_nonblock(fd):
    "Set the file descriptor to non-block."
    flags = fcntl.fcntl(fd, fcntl.F_GETFL);
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def main():
    """"The main entry."""
    arg_parser = argparse.ArgumentParser(description='A Language Server Adapter',
                                         epilog='''
                                         Examples:
                                         1. --original_response_encoding -- clangd --foo --bar
                                         2. clangd
                                         ''')
    arg_parser.add_argument("--original-response-encoding",
                            default="utf-8",
                            help="The original response encoding the adapted LS used")
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

    adapter = LsResponseAdapter(args.original_response_encoding)

    while True:
        rc = lsproc.poll()
        if rc is not None:
            logger.info("LS process exited with rc: %d", rc)
            break

        readable, _, _ = select.select([sys_stdin, lsproc_stdout, lsproc_stderr],
                                            [], [], SELECT_INTERVAL)
        if lsproc_stdout in readable:
            handle_lsproc_stdout(lsproc_stdout, adapter, sys_stdout)
        if lsproc_stderr in readable:
            handle_lsproc_stderr(lsproc_stderr, sys_stderr)
        if sys_stdin in readable:
            handle_stdin(sys_stdin, lsproc_stdin)

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    # TODO support python 2.7
    logger.info("py version: %s, cwd: %s",
                platform.python_version(),
                os.getcwd())
    main()