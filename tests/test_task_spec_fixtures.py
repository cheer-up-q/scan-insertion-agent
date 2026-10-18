
import json
from pathlib import Path

import pytest

from src.contracts.models import TaskRequirement


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "examples" / "task_specs"


@pytest.mark.parametrize(
    "case_name",
    [
        "basic_internal_scan",
        "multi_clock_scan",
        "wrapper_scan",
    ],
)
def test_task_spec_fixture_matches_contract(case_name):
    """Check that each acceptance fixture exists and matches TaskRequirement."""

    input_path = FIXTURE_DIR / f"{case_name}.md"
    expected_path = FIXTURE_DIR / f"{case_name}.expected.json"

    # Both the natural-language input and expected JSON must exist.
    assert input_path.is_file(), f"Missing input fixture: {input_path}"
    assert expected_path.is_file(), f"Missing expected JSON: {expected_path}"

    assert input_path.stat().st_size > 0, "Task specification must not be empty"

    # Load and validate the expected JSON against the shared Pydantic contract.
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    requirement = TaskRequirement(**expected)

    assert requirement.top_design == expected["top_design"]
    assert requirement.test_clocks == expected["test_clocks"]
    assert requirement.scan_enable == expected["scan_enable"]

    assert (
        requirement.internal_scan.chain_count
        == expected["internal_scan"]["chain_count"]
    )

    assert (
        requirement.output_requirements
        == expected["output_requirements"]
    )

    assert (
        requirement.unresolved_requirements
        == expected["unresolved_requirements"]
    )

    # Case-specific semantic checks.
    if case_name == "basic_internal_scan":
        assert requirement.internal_scan.edge_strategy == "rising"
        assert requirement.internal_scan.chain_count == 8
        assert requirement.wrapper_scan.enabled is False

    elif case_name == "multi_clock_scan":
        assert requirement.test_clocks == ["clk_a", "clk_b"]
        assert requirement.internal_scan.clock_domains == ["clk_a", "clk_b"]
        assert requirement.internal_scan.lockup_required is True

    elif case_name == "wrapper_scan":
        assert requirement.wrapper_scan.enabled is True
        assert requirement.wrapper_scan.scope == ["core0", "core1"]
        assert requirement.wrapper_scan.control_signals == ["wrapper_en"]
