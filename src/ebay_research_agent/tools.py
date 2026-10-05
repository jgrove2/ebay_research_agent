from pathlib import Path

from langchain_core.tools import tool


@tool
def calculate(expression: str) -> str:
    """Evaluate a simple arithmetic expression and return the result.

    Args:
        expression: A math expression using only numbers and the operators
            +, -, *, /, //, %, ** and parentheses.
    """
    allowed = set("0123456789+-*/().% ")
    if not expression or any(char not in allowed for char in expression):
        return "Invalid expression: only digits and + - * / // % ** ( ) are allowed."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except (ArithmeticError, NameError, SyntaxError, TypeError, ValueError) as exc:
        return f"Failed to evaluate: {exc}"


@tool
def read_file(path: str) -> str:
    """Read the contents of a text file and return it.

    Args:
        path: Filesystem path to the file to read.
    """
    target = Path(path).expanduser()
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return f"Failed to read {path}: {exc}"


TOOLS = [calculate, read_file]
