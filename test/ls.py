#!/usr/bin/env python
# coding: utf-8

# Fake Language Server

import sys
import time

responses = [
    "Content-Length: 12\r\n\r\nhello world.",
    'Content-Length: 1142\r\n\r\n{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":10596,"rootPath":"/home/hgw/test/eglot-gbk-demo/","rootUri":"file:///home/hgw/test/eglot-gbk-demo/","initializationOptions":null,"capabilities":{"workspace":{"applyEdit":true,"executeCommand":{"dynamicRegistration":false},"workspaceEdit":{"documentChanges":false},"didChangeWatchedFiles":{"dynamicRegistration":true},"symbol":{"dynamicRegistration":false}},"textDocument":{"synchronization":{"dynamicRegistration":false,"willSave":true,"willSaveWaitUntil":true,"didSave":true},"completion":{"dynamicRegistration":false,"completionItem":{"snippetSupport":true}},"hover":{"dynamicRegistration":false},"signatureHelp":{"dynamicRegistration":false},"references":{"dynamicRegistration":false},"definition":{"dynamicRegistration":false},"documentSymbol":{"dynamicRegistration":false},"documentHighlight":{"dynamicRegistration":false},"codeAction":{"dynamicRegistration":false},"formatting":{"dynamicRegistration":false},"rangeFormatting":{"dynamicRegistration":false},"rename":{"dynamicRegistration":false},"publishDiagnostics":{"relatedInformation":false}},"experimental":null}}}'
    u'Content-Length: 36\r\n\r\n{"content":"你好","charset":"utf-8"}',
]

utf8 = u'Content-Length: 34\r\n\r\n{"content":"你好","charset":"gbk"}'
gbk = utf8.encode('gbk')
responses.append(gbk)

for response in responses:
    sys.stdout.write(response)
    sys.stdout.flush()