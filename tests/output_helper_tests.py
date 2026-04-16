from _pytest.capture import CaptureFixture

from adbe import output_helper


def test_print_verbose_silent_when_verbose_is_disabled(capsys: CaptureFixture[str]) -> None:
    output_helper.set_verbose(enabled=False)
    output_helper.print_verbose("should_not_print")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_verbose_prints_when_verbose_is_enabled(capsys: CaptureFixture[str]) -> None:
    output_helper.set_verbose(enabled=True)
    output_helper.print_verbose("should_print")
    captured = capsys.readouterr()
    assert "should_print" in captured.out
