import json
from pathlib import Path

import pytest

from src.contracts.models import TaskRequirement
from src.task_parser import TaskParser


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "examples" / "task_specs"

CASES = (
    "basic_internal_scan",
    "multi_clock_scan",
    "wrapper_scan",
)


def _as_dict(requirement):
    if hasattr(requirement, "model_dump"):
        return requirement.model_dump()
    return requirement.dict()


def _read(case_name, suffix):
    return (FIXTURE_DIR / f"{case_name}{suffix}").read_text(encoding="utf-8")


@pytest.mark.parametrize("case_name", CASES)
def test_parser_matches_acceptance_fixture(case_name):
    """The real parser must reproduce the expected JSON field by field."""

    requirement = TaskParser().parse(_read(case_name, ".md"))
    expected = json.loads(_read(case_name, ".expected.json"))

    assert isinstance(requirement, TaskRequirement)
    assert _as_dict(requirement) == expected


def test_parser_does_not_guess_missing_fields():
    requirement = TaskParser().parse(
        "对顶层模块 chip_top 执行 Scan Insertion。测试时钟为 test_clk。"
    )

    assert requirement.top_design == "chip_top"
    assert requirement.test_clocks == ["test_clk"]
    assert requirement.resets == []
    assert requirement.scan_enable is None
    assert requirement.internal_scan.chain_count is None
    assert requirement.internal_scan.chain_length is None
    assert requirement.internal_scan.edge_strategy is None
    assert requirement.internal_scan.lockup_required is None
    assert requirement.wrapper_scan.enabled is False
    assert requirement.output_requirements == []
    assert requirement.unresolved_requirements == []


def test_multiple_clocks_and_resets_keep_source_order():
    requirement = TaskParser().parse(
        "测试时钟包括 clk_a、clk_b 和 clk_c。"
        "复位信号包括 rst_n 与 por_n。"
    )

    assert requirement.test_clocks == ["clk_a", "clk_b", "clk_c"]
    assert requirement.resets == ["rst_n", "por_n"]


def test_ambiguous_chain_count_is_unresolved():
    requirement = TaskParser().parse("对顶层模块 chip_top 执行 Scan Insertion。尽量减少 Scan Chain 数量。")

    assert requirement.internal_scan.chain_count is None
    assert "Scan chain count is not explicitly specified." in requirement.unresolved_requirements


def test_maximum_chain_length_is_not_forced_into_chain_length():
    requirement = TaskParser().parse("每条 Scan Chain 最大长度不能超过 200。")

    assert requirement.internal_scan.chain_length is None
    assert any(
        "Maximum scan chain length" in item
        for item in requirement.unresolved_requirements
    )


def test_exact_chain_length_is_parsed():
    requirement = TaskParser().parse("每条 Scan Chain 长度设置为 100。")

    assert requirement.internal_scan.chain_length == 100
    assert requirement.unresolved_requirements == []


def test_wrapper_control_signal_implies_wrapper_enabled():
    requirement = TaskParser().parse("Wrapper 控制信号为 wrapper_en。")

    assert requirement.wrapper_scan.enabled is True
    assert requirement.wrapper_scan.control_signals == ["wrapper_en"]
    assert (
        "Wrapper scope must be determined from design analysis."
        in requirement.unresolved_requirements
    )


def test_output_requirements_are_normalized_and_ordered():
    requirement = TaskParser().parse(
        "需要生成 Post-scan Netlist、CTL、SCANDEF、Scan Report 和 DFT Report。"
    )

    assert requirement.output_requirements == [
        "post_scan_netlist",
        "ctl",
        "scandef",
        "scan_report",
        "dft_report",
    ]


def test_limitations_conflict_is_reported_but_value_is_kept():
    requirement = TaskParser().parse(
        "Scan Enable 为 scan_en。",
        limitations="禁止使用 scan_en 作为测试控制信号。",
    )

    assert requirement.scan_enable == "scan_en"
    assert (
        "Conflict detected between task_spec.md and limitations.md for scan_enable."
        in requirement.unresolved_requirements
    )


def test_modification_constraint_is_not_a_usage_conflict():
    requirement = TaskParser().parse(
        "Scan Enable 为 scan_en。",
        limitations="禁止修改 scan_en 信号定义。",
    )

    assert requirement.scan_enable == "scan_en"
    assert requirement.unresolved_requirements == []


def test_top_design_without_name_is_unresolved():
    requirement = TaskParser().parse("对当前设计执行 Scan Insertion。")

    assert requirement.top_design is None
    assert (
        "Top design must be determined from design analysis."
        in requirement.unresolved_requirements
    )


def test_reverse_style_signal_expressions():
    requirement = TaskParser().parse(
        "clk_a、clk_b 均作为 Scan Clock。"
        "rst_n 和 por_n 均作为复位信号。"
        "scan_en 作为扫描使能信号。"
    )

    assert requirement.test_clocks == ["clk_a", "clk_b"]
    assert requirement.resets == ["rst_n", "por_n"]
    assert requirement.scan_enable == "scan_en"


def test_wrapper_scope_from_enable_sentence():
    requirement = TaskParser().parse("对 core0 和 core1 启用 Wrapper Scan。")

    assert requirement.wrapper_scan.enabled is True
    assert requirement.wrapper_scan.scope == ["core0", "core1"]
    assert requirement.unresolved_requirements == []


def test_parse_file_matches_parse_text():
    requirement = TaskParser().parse_file(
        str(FIXTURE_DIR / "basic_internal_scan.md")
    )
    expected = json.loads(
        (FIXTURE_DIR / "basic_internal_scan.expected.json").read_text(
            encoding="utf-8"
        )
    )

    assert _as_dict(requirement) == expected
