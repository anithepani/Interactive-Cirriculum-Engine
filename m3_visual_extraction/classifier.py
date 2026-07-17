class FrameClassifier:
    """
    Classifies OCR text extracted from video frames.

    Possible classes:
    - python_code
    - document
    """

    def __init__(self):
        # Comprehensive Python keywords
        self.python_keywords = {
            # Core keywords
            "def", "class", "import", "from", "print",
            "return", "for", "while", "if", "elif",
            "else", "try", "except", "finally",
            "lambda", "with", "yield", "async", "await",
            "pass", "break", "continue", "global", "nonlocal",
            "raise", "assert", "del",
            
            # Common built-in functions
            "range", "len", "sum", "min", "max", "sorted",
            "list", "dict", "set", "tuple", "str", "int",
            "float", "bool", "type", "isinstance", "hasattr",
            "getattr", "setattr", "dir", "help", "open",
            "zip", "map", "filter", "enumerate", "reversed",
            
            # Common constants
            "true", "false", "none", "self", "cls",
            "__init__", "__str__", "__repr__", "__call__",
            "__main__", "__name__", "__file__", "__doc__",
            
            # Comparison and assignment operators
            "=", "==", "!=", "<=", ">=", "<", ">",
            "+=", "-=", "*=", "/=", "//=", "%=",
            "**=", "&=", "|=", "^=", ">>=", "<<=",
            
            # Punctuation and structure
            "(", ")", "[", "]", "{", "}",
            ":", ",", ".", "@", "*", "**",
            "/", "//", "%", "+", "-", "&",
            "|", "^", "~", ">>", "<<",
            
            # Common Python patterns
            "if __name__", "def __init__", "class",
            "import ", "from ", "as ",
            "with ", "try:", "except:", "finally:",
            "elif ", "else:", "for ", "while ",
            "in ", "is ", "not in", "is not",
            
            # Popular libraries (to catch imports)
            "numpy", "pandas", "matplotlib", "sklearn",
            "tensorflow", "torch", "keras", "flask",
            "django", "requests", "beautifulsoup", "scrapy",
            "pytest", "unittest", "logging", "json",
            "os", "sys", "re", "datetime", "time",
            
            # Common variable naming patterns
            "_", "__", "self.", "cls.",
        }
        
        # Patterns that strongly indicate Python code
        self.strong_patterns = {
            "def ", "class ", "import ", "from ", "print(",
            "range(", "len(", "self.", "cls.",
            "if __name__", "__init__", "__str__",
            "for ", "while ", "lambda ", "yield ",
            "try:", "except:", "finally:",
            "with ", "as ", "return ",
            "async def", "await ",
        }
        
        # Patterns that indicate document text (to avoid false positives)
        self.document_patterns = {
            "introduction", "chapter", "section", "figure",
            "table", "equation", "reference", "bibliography",
            "abstract", "conclusion", "appendix", "theorem",
            "lemma", "proof", "definition", "example",
            "algorithm", "procedure", "methodology", "results",
            "discussion", "analysis", "framework", "approach",
        }

    def count_matches(self, text):
        """
        Counts how many Python keywords appear in the text.
        """
        t = text.lower()
        return sum(
            keyword in t
            for keyword in self.python_keywords
        )

    def has_strong_pattern(self, text):
        """
        Checks for strong Python code patterns.
        """
        t = text.lower()
        return any(pattern in t for pattern in self.strong_patterns)

    def has_document_pattern(self, text):
        """
        Checks for document-like patterns.
        """
        t = text.lower()
        document_count = sum(1 for pattern in self.document_patterns if pattern in t)
        return document_count >= 2  # Multiple document patterns suggest document

    def classify(self, text):
        """
        Classifies text as either 'python_code' or 'document'.
        """
        if not text or not text.strip():
            return "document"

        t = text.lower()
        
        # First, check if it's clearly a document
        if self.has_document_pattern(t) and not self.has_strong_pattern(t):
            return "document"
        
        # Count keyword matches
        score = self.count_matches(t)
        
        # Check for strong patterns (these are highly indicative of code)
        if self.has_strong_pattern(t):
            # Even with fewer matches, strong patterns suggest code
            if score >= 1:
                return "python_code"
        
        # Require multiple matches for standard classification
        if score >= 3:  # Increased threshold to reduce false positives
            return "python_code"
        
        # Check for code-like characteristics (e.g., indentation, function calls)
        if "(" in text and ")" in text and any(c in text for c in ["=", ":", ","]):
            if score >= 2:
                return "python_code"
        
        # If text has parentheses and common code symbols but few keyword matches
        if "(" in text and ")" in text and "=" in text and ":" in text:
            return "python_code"
        
        return "document"