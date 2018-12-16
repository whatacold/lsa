#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys

sys.path.append("..")
from lsa import LsResponseAdapter

class LsResponseAdapterTest(unittest.TestCase):
    valid_lsp_responses = [
        b"Content-Length: 5\r\n\r\nhello",
        b"Content-Length: 5\r\nxxxxxxx\r\n\r\nhello",
        b"Content-Length: 5\r\n\r\nhelloContent-Length: 5\r\nxxxxxxx\r\n\r\nhello",
        b"Content-Length: 5\r\n\r\nhello-----non lsp content-----Content-Length: 5\r\nxxxxxxx\r\n\r\nhello",
        b"foobarContent-Length: 5\r\n\r\nhello-----non lsp content-----Content-Length: 5\r\nxxxxxxx\r\n\r\nhello",
    ]

    def test_complete_responses(self):
        """Test case for complete LSP response."""
        adapter = LsResponseAdapter()
        for response in self.valid_lsp_responses:
            output = adapter.adapt_response(response)
            self.assertEqual(response, output)

    def test_slow_response(self):
        """Test case for adapting slow response of LS."""
        adapter = LsResponseAdapter()
        for response in self.valid_lsp_responses:
            for every_len in [3, 6, 12, 20]:
                i = 0
                output = b''
                while i < len(response):
                    this_input = response[i:(i + every_len)]
                    output = output + adapter.adapt_response(this_input)
                    i = i + every_len
                self.assertEqual(response, output)

    def test_encoding(self):
        """
        Test case for adapting LSP response encoding.

        UTF-8 output is expected after adapting, no matter
        what encoding the original output uses.
        """
        messages = [
            "hello world means 你好世界。",
            "这是一句长长长长长长长长长长长长长长长长长长的句子。",
        ]

        for encoding in ['utf-8', 'gbk']:
            adapter = LsResponseAdapter(encoding)
            for message in messages:
                msg_utf8_bytes = message.encode('utf-8')
                expected_output = "Content-Length: {}\r\n\r\n".format(len(msg_utf8_bytes)) \
                                                              .encode() + \
                                                              msg_utf8_bytes

                input_bytes = message.encode(encoding)
                input_bytes = "Content-Length: {}\r\n\r\n".format(len(input_bytes)) \
                                                          .encode() + \
                                                          input_bytes
                output = adapter.adapt_response(input_bytes)
                self.assertEqual(expected_output, output)

if __name__ == "__main__":
    unittest.main()
