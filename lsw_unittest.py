#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from lsw import LsOutputAdapter

class LsOutputAdapterTest(unittest.TestCase):
    valid_messages = [
        b"Content-Length: 5\r\n\r\nhello",
        b"Content-Length: 5\r\nxxxxxxx\r\n\r\nhello",
        b"Content-Length: 5\r\n\r\nhelloContent-Length: 5\r\nxxxxxxx\r\n\r\nhello",
        b"Content-Length: 5\r\n\r\nhello-----non lsp content-----Content-Length: 5\r\nxxxxxxx\r\n\r\nhello",
        b"foobarContent-Length: 5\r\n\r\nhello-----non lsp content-----Content-Length: 5\r\nxxxxxxx\r\n\r\nhello",
    ]

    def test_complete_messages(self):
        adapter = LsOutputAdapter()
        for input in self.valid_messages:
            output = adapter.process_input(input)
            self.assertEqual(input, output)

    def test_slow_output(self):
        adapter = LsOutputAdapter()
        for input in self.valid_messages:
            for every_len in [3, 6, 12, 20]:
                i = 0
                output = b''
                while i < len(input):
                    this_input = input[i:(i + every_len)]
                    output = output + adapter.process_input(this_input)
                    i = i + every_len
                self.assertEqual(input, output)

    def test_output_as_utf8(self):
        "UTF-8 output is expected, no matter what encoding the original output uses."
        messages = [
            "hello world means 你好",
            "这是一句长长长长长长长长长长长长长长长长长长的句子。",
        ]

        for encoding in ['utf-8', 'gbk']:
            adapter = LsOutputAdapter(encoding)
            for input in messages:
                print("test input in:", encoding)

                input_utf8_bytes = input.encode('utf-8')
                expected_output = "Content-Length: {}\r\n\r\n".format(len(input_utf8_bytes)) \
                                                              .encode() + \
                                                              input_utf8_bytes

                input_bytes = input.encode(encoding)
                input_bytes = "Content-Length: {}\r\n\r\n".format(len(input_bytes)) \
                                                          .encode() + \
                                                          input_bytes
                output = adapter.process_input(input_bytes)
                self.assertEqual(expected_output, output)

if __name__ == "__main__":
    unittest.main()
