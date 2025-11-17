# rag_service.py
# Chunking service for different programming languages

def chunk_java_file(code: str):
    """Chunk Java code - split by 1000 chars for now"""
    return [code[i:i+1000] for i in range(0, len(code), 1000)]

def chunk_js_file(code: str):
    """Chunk JavaScript/JSX code - split by 1000 chars for now"""
    return [code[i:i+1000] for i in range(0, len(code), 1000)]

def chunk_python_file(code: str):
    """Chunk Python code - split by 1000 chars for now"""
    return [code[i:i+1000] for i in range(0, len(code), 1000)]

def chunk_typescript_file(code: str):
    """Chunk TypeScript/TSX code - split by 1000 chars for now"""
    return [code[i:i+1000] for i in range(0, len(code), 1000)]

def chunk_generic_file(code: str):
    """Generic chunking for any code file"""
    return [code[i:i+1000] for i in range(0, len(code), 1000)]