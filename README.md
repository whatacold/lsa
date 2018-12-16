A trivial Language Server adapter

# Why?

As there are some projects using non-UTF-8 encoding, e.g. GBK, at work,
and LSP specification only supports UTF-8, I need a way to adapt the response
from GBK to UTF-8 encoding.

# How to use

1. Download `lsa.py` from this repo, or clone it if you like.
2. Replace whatever language server you use with `lsa.py`

   For me, I start the server with `eglot` in Emacs like this:

        (defcustom eglot-ls-output-encoding "utf-8"
          "The LS's output encoding")

        (defun whatacold/eglot-ccls-contact (interactive-p)
          "A contact function to assemble args for ccls.
        Argument INTERACTIVE-P indicates where it's called interactively."
          (let ((json-object-type 'plist)
                (json-array-type 'list)
                result)
            (push (format "-log-file=/tmp/ccls-%s.log"
                          (file-name-base
                           (directory-file-name
                            (car
                             (project-roots
                              (project-current))))))
                  result)
            (when whatacold/ccls-init-args
              (push (format "-init=%s" (json-encode
                                        whatacold/ccls-init-args))
                    result))
            (push "ccls" result)
        
            ; adapt the response encoding
            (unless (equal eglot-ls-output-encoding "utf-8")
              (dolist (item (reverse (list "lsa.py"
                                           (concat "--original-response-encoding="
                                                   eglot-ls-output-encoding)
                                           "--log-level=DEBUG"
                                           "--")))
                (push item result)))
            result))

# Notes

- Only Python 3 is currently supported