"""Unit tests for Jinja2 templates — no DB, no IO, no LLM calls."""

from jinja2 import Environment, FileSystemLoader
from tests.utils import get_templates_dir


def _make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(get_templates_dir())), autoescape=False
    )


class TestExtractionTemplate:
    """Tests for templates/extraction.jinja (outbound tasking email)."""

    def test_renders_coordinate(self) -> None:
        env = _make_env()
        tmpl = env.get_template("extraction.jinja")
        rendered = tmpl.render(coordinate="8A2F/9B4C", parameter="vad")
        assert "8A2F/9B4C" in rendered

    def test_renders_parameter(self) -> None:
        env = _make_env()
        tmpl = env.get_template("extraction.jinja")
        rendered = tmpl.render(coordinate="8A2F/9B4C", parameter="vad")
        assert "vad" in rendered

    def test_contains_all_six_measurement_fields(self) -> None:
        env = _make_env()
        tmpl = env.get_template("extraction.jinja")
        rendered = tmpl.render(coordinate="8A2F/9B4C", parameter="vad")
        assert "PARAM" in rendered
        assert "Time of measurement" in rendered or "time of measurement" in rendered
        assert "Location" in rendered or "location" in rendered
        assert "Sleep quality" in rendered or "sleep quality" in rendered
        assert "Psychological state" in rendered or "psychological state" in rendered
        assert "Social Field" in rendered or "social field" in rendered

    def test_does_not_contain_target_statement(self) -> None:
        """Double-blind: template must NOT leak target identity."""
        env = _make_env()
        tmpl = env.get_template("extraction.jinja")
        rendered = tmpl.render(coordinate="8A2F/9B4C", parameter="vad")
        assert "target statement" not in rendered.lower()
        assert "true target" not in rendered.lower()


class TestExtractionPromptTemplate:
    """Tests for templates/extraction_prompt.jinja (Ollama extraction prompt)."""

    def test_extract_prompt_contains_coordinate_and_parameter(self) -> None:
        """Render template with known coordinate, parameter, email_body and assert all three appear in output."""
        env = _make_env()
        tmpl = env.get_template("extraction_prompt.jinja")
        email_body = "PARAM (vad): 75\nLocation: Bucharest"
        rendered = tmpl.render(
            coordinate="8A2F/9B4C",
            parameter="vad",
            email_body=email_body,
        )
        assert "8A2F/9B4C" in rendered
        assert "vad" in rendered
        assert email_body in rendered
