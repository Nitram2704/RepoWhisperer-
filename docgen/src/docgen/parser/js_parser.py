from pathlib import Path

import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser, Query, QueryCursor

from docgen.models import CodeChunk

# Constants - Instantiated once
JS_LANGUAGE = Language(tsjs.language())
TS_LANGUAGE = Language(tsts.language_typescript())
TSX_LANGUAGE = Language(tsts.language_tsx())

_js_parser = Parser(JS_LANGUAGE)
_ts_parser = Parser(TS_LANGUAGE)
_tsx_parser = Parser(TSX_LANGUAGE)

# Simplified query for maximum compatibility across JS/TS/TSX grammars
# We extract the name field via node.child_by_field_name("name") in Python
_JS_TS_QUERY_SRC = """
(function_declaration) @chunk
(class_declaration) @chunk
(method_definition) @chunk
"""

# Instantiating Queries and Cursors once for efficiency
_JS_QUERY = Query(JS_LANGUAGE, _JS_TS_QUERY_SRC)
_TS_QUERY = Query(TS_LANGUAGE, _JS_TS_QUERY_SRC)
_TSX_QUERY = Query(TSX_LANGUAGE, _JS_TS_QUERY_SRC)

_JS_CURSOR = QueryCursor(_JS_QUERY)
_TS_CURSOR = QueryCursor(_TS_QUERY)
_TSX_CURSOR = QueryCursor(_TSX_QUERY)


def parse_js_ts(path: Path, source: str) -> list[CodeChunk]:
    """Parse JavaScript, TypeScript, or TSX files using Tree-Sitter."""
    suffix = path.suffix.lower()
    
    if suffix == ".tsx":
        parser = _tsx_parser
        query = _TSX_QUERY
        cursor = _TSX_CURSOR
        lang_name = "typescript"
    elif suffix == ".ts":
        parser = _ts_parser
        query = _TS_QUERY
        cursor = _TS_CURSOR
        lang_name = "typescript"
    else:  # .js
        parser = _js_parser
        query = _JS_QUERY
        cursor = _JS_CURSOR
        lang_name = "javascript"

    tree = parser.parse(bytes(source, "utf8"))
    captures = cursor.captures(tree.root_node)
    
    source_lines = source.splitlines()
    chunks = []

    if "chunk" not in captures:
        return []

    for node in captures["chunk"]:
        name_node = node.child_by_field_name("name")
        name = name_node.text.decode("utf8") if name_node else "<anonymous>"
        
        chunk_type = "class" if node.type == "class_declaration" else "function"
        
        # tree-sitter is 0-indexed
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Extract content
        # Ensure we don't go out of bounds
        content = "\n".join(source_lines[start_line - 1 : end_line])
        
        parent = None
        if node.type == "method_definition":
            # Attempt to find parent class name
            p = node.parent
            while p:
                if p.type == "class_declaration":
                    p_name_node = p.child_by_field_name("name")
                    if p_name_node:
                        parent = p_name_node.text.decode("utf8")
                    break
                p = p.parent

        chunks.append(
            CodeChunk(
                file_path=str(path),
                language=lang_name,
                chunk_type=chunk_type,
                name=name,
                content=content,
                start_line=start_line,
                end_line=end_line,
                parent=parent,
            )
        )
        
    return chunks
