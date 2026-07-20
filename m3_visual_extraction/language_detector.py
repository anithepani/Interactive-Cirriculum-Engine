class LanguageDetector:
    """
    Detects whether the extracted text is
    Python code or a normal document.
    """

    def detect(self, text):
        if not text or not text.strip():
            return "document"

        t = text.lower()
        
        # ============================================================
        # COMPLETE PYTHON KEYWORDS (All 35 Python 3 keywords)
        # ============================================================
        python_keywords = [
            # Control flow
            "if ", "elif ", "else:", "for ", "while ", "break", 
            "continue", "pass", "return", "yield", "yield from",
            
            # Exception handling
            "try:", "except", "finally:", "raise", "assert",
            
            # Function and class definitions
            "def ", "class ", "lambda ", "async def", "await",
            
            # Import statements
            "import ", "from ", "as ",
            
            # Variable handling
            "global ", "nonlocal ", "del ",
            
            # Boolean and None
            "true", "false", "none",
            
            # Operators
            " and ", " or ", " not ", " is ", " in ",
            "is not", "not in",
            
            # Assignment operators
            "=", "+=", "-=", "*=", "/=", "//=", "%=",
            "**=", "&=", "|=", "^=", ">>=", "<<=",
            
            # Comparison operators
            "==", "!=", "<=", ">=", "<", ">",
            
            # Bitwise operators
            "&", "|", "^", "~", "<<", ">>",
            
            # Special methods (dunder methods)
            "__init__", "__str__", "__repr__", "__call__",
            "__main__", "__name__", "__file__", "__doc__",
            "__new__", "__del__", "__len__", "__getitem__",
            "__setitem__", "__delitem__", "__iter__", "__next__",
            "__enter__", "__exit__", "__eq__", "__ne__",
            "__lt__", "__le__", "__gt__", "__ge__",
            "__add__", "__sub__", "__mul__", "__truediv__",
            
            # ============================================================
            # BUILT-IN FUNCTIONS (All 69 built-in functions)
            # ============================================================
            "abs(", "all(", "any(", "ascii(", "bin(", "bool(",
            "breakpoint(", "bytearray(", "bytes(", "callable(",
            "chr(", "classmethod(", "compile(", "complex(",
            "delattr(", "dict(", "dir(", "divmod(", "enumerate(",
            "eval(", "exec(", "filter(", "float(", "format(",
            "frozenset(", "getattr(", "globals(", "hasattr(",
            "hash(", "help(", "hex(", "id(", "input(", "int(",
            "isinstance(", "issubclass(", "iter(", "len(",
            "list(", "locals(", "map(", "max(", "memoryview(",
            "min(", "next(", "object(", "oct(", "open(",
            "ord(", "pow(", "print(", "property(", "range(",
            "repr(", "reversed(", "round(", "set(", "setattr(",
            "slice(", "sorted(", "staticmethod(", "str(",
            "sum(", "super(", "tuple(", "type(", "vars(",
            "zip(", "__import__(",
            
            # ============================================================
            # COMMON BUILT-IN EXCEPTIONS
            # ============================================================
            "exception", "valueerror", "typeerror", "keyerror",
            "indexerror", "attributeerror", "ioerror", "oserror",
            "importerror", "syntaxerror", "indentationerror",
            
            # ============================================================
            # COMMON STANDARD LIBRARY MODULES
            # ============================================================
            "import os", "import sys", "import re", "import json",
            "import csv", "import math", "import random",
            "import datetime", "import time", "import logging",
            "import threading", "import multiprocessing",
            "import subprocess", "import socket", "import http",
            "import urllib", "import xml", "import html",
            "import hashlib", "import base64", "import itertools",
            "import collections", "import functools", "import operator",
            "import string", "import io", "import pathlib",
            
            # ============================================================
            # POPULAR THIRD-PARTY LIBRARIES
            # ============================================================
            "import numpy", "import pandas", "import matplotlib",
            "import seaborn", "import scipy", "import sklearn",
            "import tensorflow", "import torch", "import keras",
            "import flask", "import django", "import requests",
            "import beautifulsoup", "import scrapy", "import selenium",
            "import pytest", "import unittest", "import coverage",
            
            # ============================================================
            # PYTHON SYNTAX AND PUNCTUATION
            # ============================================================
            "(", ")", "[", "]", "{", "}", ":", ",", ".", "@",
            "*", "**", "/", "//", "%", "+", "-",
            
            # ============================================================
            # COMMON CODE PATTERNS
            # ============================================================
            "if __name__", "def __init__", "class",
            "with ", "as ",
            "self.", "cls.", "super()",
            "raise ", "assert ",
            "yield ", "yield from",
            "nonlocal ", "global ",
            "del ", "pass",
            "async ", "await ",
            "match ", "case ",  # Python 3.10+ pattern matching
            "_", "__",  # Special naming conventions
            
            # ============================================================
            # DOCUMENTATION AND COMMENTS
            # ============================================================
            '"""', "'''",  # Docstrings
            "#",  # Comments
            "TODO", "FIXME", "NOTE",  # Common comment markers
            
            # ============================================================
            # COMMON VARIABLE NAMES IN CODE
            # ============================================================
            "data", "result", "value", "item", "element",
            "index", "counter", "total", "count", "length",
            "array", "list", "dict", "set", "tuple",
            "file", "path", "name", "age", "score",
            
            # ============================================================
            # COMMON FUNCTION NAMES
            # ============================================================
            "main()", "calculate", "compute", "process",
            "generate", "analyze", "predict", "train",
            "test", "evaluate", "validate", "save", "load",
            "read", "write", "open", "close", "connect",
            "disconnect", "send", "receive", "fetch",
        ]
        
        # ============================================================
        # PATTERNS THAT STRONGLY INDICATE PYTHON CODE
        # ============================================================
        strong_patterns = [
            "def ", "class ", "import ", "from ", "print(",
            "range(", "len(", "self.", "cls.",
            "if __name__", "__init__", "__str__",
            "for ", "while ", "lambda ", "yield ",
            "try:", "except:", "finally:",
            "with ", "as ", "return ",
            "async def", "await ",
            "super()", "raise ", "assert ",
            '"""', "'''", "#",
            "import os", "import sys", "import json",
            "if __name__ == '__main__'",
        ]
        
        # ============================================================
        # DOCUMENT PATTERNS (to reduce false positives)
        # ============================================================
        document_patterns = [
            "introduction", "chapter", "section", "figure",
            "table", "equation", "reference", "bibliography",
            "abstract", "conclusion", "appendix", "theorem",
            "lemma", "proof", "definition", "example",
            "algorithm", "procedure", "methodology", "results",
            "discussion", "analysis", "framework", "approach",
            "overview", "background", "related work", "future work",
            "acknowledgment", "reference", "citation", "author",
            "published", "volume", "issue", "pages", "journal",
            "conference", "workshop", "symposium", "proceedings",
            "doi", "issn", "isbn", "figure", "table",
            "equation", "formula", "algorithm",
        ]
        
        # ============================================================
        # CLASSIFICATION LOGIC
        # ============================================================
        
        # Check for document patterns first
        doc_count = sum(1 for pattern in document_patterns if pattern in t)
        if doc_count >= 3 and not any(p in t for p in strong_patterns[:5]):
            return "document"
        
        # Count Python matches
        matches = sum(1 for keyword in python_keywords if keyword in t)
        
        # Check for strong patterns
        strong_match = any(pattern in t for pattern in strong_patterns)
        
        # Check for indentation (common in Python)
        has_indentation = "\n    " in text or "\n\t" in text or "\n  " in text
        
        # Check for function calls with parentheses
        has_function_call = "(" in text and ")" in text and any(
            func in t for func in ["(", ")"] 
        )
        
        # Check for colons at end of lines (common in Python)
        has_colon_pattern = any(
            line.strip().endswith(":") 
            for line in text.split("\n") 
            if line.strip()
        )
        
        # Classification with multiple criteria
        score = 0
        
        # Add points for each indicator
        if matches >= 1:
            score += matches
        if strong_match:
            score += 5  # Heavy weight for strong patterns
        if has_indentation:
            score += 2
        if has_function_call and matches >= 2:
            score += 2
        if has_colon_pattern:
            score += 3
        
        # Final decision
        if score >= 3:
            return "python_code"
        
        # Edge cases: obvious code with few keywords
        if strong_match and matches >= 1:
            return "python_code"
        
        if has_indentation and matches >= 2:
            return "python_code"
        
        if has_colon_pattern and matches >= 2:
            return "python_code"
        
        return "document"