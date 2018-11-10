#!/usr/bin/env python
# coding: utf-8

# Fake Language Server

import sys
import time
import os

responses = [
    "hello world.",
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":10596,"rootPath":"/home/hgw/test/eglot-gbk-demo/","rootUri":"file:///home/hgw/test/eglot-gbk-demo/","initializationOptions":null,"capabilities":{"workspace":{"applyEdit":true,"executeCommand":{"dynamicRegistration":false},"workspaceEdit":{"documentChanges":false},"didChangeWatchedFiles":{"dynamicRegistration":true},"symbol":{"dynamicRegistration":false}},"textDocument":{"synchronization":{"dynamicRegistration":false,"willSave":true,"willSaveWaitUntil":true,"didSave":true},"completion":{"dynamicRegistration":false,"completionItem":{"snippetSupport":true}},"hover":{"dynamicRegistration":false},"signatureHelp":{"dynamicRegistration":false},"references":{"dynamicRegistration":false},"definition":{"dynamicRegistration":false},"documentSymbol":{"dynamicRegistration":false},"documentHighlight":{"dynamicRegistration":false},"codeAction":{"dynamicRegistration":false},"formatting":{"dynamicRegistration":false},"rangeFormatting":{"dynamicRegistration":false},"rename":{"dynamicRegistration":false},"publishDiagnostics":{"relatedInformation":false}},"experimental":null}}}',
    u'{"content":"你好","charset":"utf-8"}',
]

sys_stdout = os.fdopen(sys.stdout.fileno(), "wb")

for response in responses:
    encoding = sys.argv[1]
    response_byte = response.encode(encoding)
    sys_stdout.write("Content-Length: {}\r\n\r\n".format(len(response_byte)).encode(encoding))
    sys_stdout.write(response_byte)
    sys_stdout.flush()