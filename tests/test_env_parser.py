from pathlib import Path
from src.gui.env_controls import parse_env_example, read_env_values


def test_parse_env_example_reads_pairs(tmp_path: Path) -> None:
    ex = tmp_path / ".env.example"
    ex.write_text("WAHA_HOST=\nDJANGO_DEBUG=true\nJWT_SECRET=\n", encoding="utf-8")
    pairs = parse_env_example(ex)
    assert ("WAHA_HOST", "") in pairs
    assert ("DJANGO_DEBUG", "true") in pairs
    assert ("JWT_SECRET", "") in pairs


def test_read_env_values_reads_dict(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("A=1\nB=2\n# C=3\n", encoding="utf-8")
    data = read_env_values(env)
    assert data == {"A": "1", "B": "2"}

