from dataclasses import dataclass
from typing import Optional


@dataclass
class CodeChunk:
    """Shared data contract for all pipeline stages.

    Represents a semantically meaningful unit of source code
    (function, class, module, or block) extracted by the parser.
    """

    file_path: str
    language: str
    chunk_type: str
    name: str
    content: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    parent: Optional[str] = None
