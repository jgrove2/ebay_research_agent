from repair_agent.tools import calculate, read_file


def test_calculate() -> None:
    assert calculate.invoke({"expression": "2 + 3 * 4"}) == "14"


def test_calculate_rejects_invalid() -> None:
    result = calculate.invoke({"expression": "__import__('os')"})
    assert result.startswith("Invalid expression")


def test_read_file(tmp_path) -> None:
    target = tmp_path / "hello.txt"
    target.write_text("hi", encoding="utf-8")
    assert read_file.invoke({"path": str(target)}) == "hi"


def test_read_file_missing() -> None:
    result = read_file.invoke({"path": "/nonexistent/does-not-exist.txt"})
    assert result.startswith("Failed to read")
