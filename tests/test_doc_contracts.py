"""Documentation and action-catalog consistency tests owned by A.

These tests deliberately do not import ``src.task_parser``.  On ``dev`` the
parser package is still empty, so importing it would turn the whole test
directory into a collection error.  Parser behaviour tests belong to the
parser pull request.
"""

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCHEMA_PATH = ROOT / "schemas" / "dofile_actions.yaml"

OUTPUT_KEY_MAP = (
    ("post_scan_netlist", "post_scan_netlist", "deliverables"),
    ("scan_report", "scan_chains", "reports"),
    ("dft_report", "dft_drc", "reports"),
    ("wrapper_report", "wrapper_report", "reports"),
    ("ctl", "ctl", "deliverables"),
    ("scandef", "scandef", "deliverables"),
)


@pytest.fixture(scope="module")
def schema():
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def actions(schema):
    return {action["action_id"]: action for action in schema["actions"]}


def _doc(name):
    return (DOCS / name).read_text(encoding="utf-8")


def test_schema_version_is_0_2_0(schema):
    assert schema["schema_version"] == "0.2.0"


def test_action_ids_are_unique(schema):
    ids = [action["action_id"] for action in schema["actions"]]
    assert len(ids) == len(set(ids))


def test_all_command_templates_remain_unresolved(schema):
    assert schema["command_syntax_status"] == "needs_official_reference"
    assert all(action["command_template"] is None for action in schema["actions"])
    assert all(
        action["command_status"] == "needs_official_reference"
        for action in schema["actions"]
    )


def test_required_parameters_are_typed(schema):
    registry = schema["parameter_types"]
    for action in schema["actions"]:
        for name in action["required_parameters"]:
            assert name in registry, (
                f"{action['action_id']} uses unregistered parameter {name!r}"
            )


def test_stages_are_declared(schema):
    stages = set(schema["generation_order"])
    for action in schema["actions"]:
        assert action["stage"] in stages, (
            f"{action['action_id']} uses undeclared stage {action['stage']!r}"
        )


def test_dependency_targets_exist(schema, actions):
    for action in schema["actions"]:
        for dependency in action.get("depends_on", []):
            assert dependency in actions
        for dependency in action.get("mutually_exclusive_with", []):
            assert dependency in actions
        for chain in action.get("depends_on_any", []):
            for dependency in chain:
                assert dependency in actions


def test_critical_actions_exist(actions):
    for action_id in (
        "report.write_wrapper",
        "signal.set_reset_polarity",
        "signal.add_test_mode",
    ):
        assert action_id in actions


def test_chain_length_is_exact_fixed_length(schema):
    assert (
        schema["parameter_types"]["chain_length"]["semantics"]
        == "exact_fixed_length"
    )


def test_insertion_entry_points_are_exclusive(actions):
    insert = actions["scan.insert"]
    assert set(insert["mutually_exclusive_with"]) == {
        "scan.replace_cells",
        "scan.stitch_chains",
    }

    for granular in ("scan.replace_cells", "scan.stitch_chains"):
        assert "scan.insert" in actions[granular]["mutually_exclusive_with"]

    # The granular pair remains a valid ordered sequence.
    assert "scan.replace_cells" in actions["scan.stitch_chains"]["depends_on"]


def test_wrapper_report_depends_on_wrapper_enable(actions):
    action = actions["report.write_wrapper"]
    assert "wrapper.enable" in action["depends_on"]
    assert action["validator"]["report_key"] == "wrapper_report"


def test_validator_report_keys_use_runtime_keys(schema):
    allowed = {"scan_chains", "dft_drc", "wrapper_report", "lec"}
    for action in schema["actions"]:
        validator = action.get("validator")
        if validator is not None:
            assert validator["report_key"] in allowed


def test_interfaces_define_the_only_output_key_mapping():
    text = _doc("interfaces.md")

    for requirement_key, runtime_key, slot in OUTPUT_KEY_MAP:
        assert f"`{requirement_key}`" in text
        assert f"`{runtime_key}`" in text
        assert f"`{slot}`" in text

    assert "scan_chain_report" not in text, "retired interface alias reappeared"
    assert "same_edge" not in text, "retired edge value reappeared"


def test_no_doc_uses_retired_output_or_edge_names():
    for path in DOCS.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "scan_chain_report" not in text, f"retired alias in {path}"
        assert "same_edge" not in text, f"retired edge value in {path}"
        assert "最大链长" not in text, f"retired chain-length semantics in {path}"


def test_dofile_mapping_removes_max_length_semantics():
    text = _doc("dofile_mapping.md")

    assert "最大链长" not in text
    assert "容量预检" in text
    assert "逐链" in text
    assert "report.write_wrapper" in text


def test_requirement_mapping_cross_references_capacity_precheck():
    text = _doc("task_requirement_mapping.md")

    assert "容量预检" in text
    assert "不构成长度验收" in text
    assert "显式禁用优先" in text


def test_evidence_record_exists():
    record = DOCS / "evidence" / "2026-10-19" / "github-state.md"
    assert record.is_file()
    assert "e6ab0648001654b343194d84c9cbf949b195bdc8" in record.read_text(
        encoding="utf-8"
    )
