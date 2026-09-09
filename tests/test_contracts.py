from src.contracts.models import (
    CaseInput,
    TaskType,
    TaskRequirement,
    ToolRunResult,
    ExitStatus,
)


def test_case_input():
    case = CaseInput(
        case_id="public_case_1",
        task_type=TaskType.TASK1,
        input_dir="input",
        pre_scan_netlist="input/netlist/pre_scan.v",
        liberty_file="input/lib/stdcells.lib",
        task_spec="input/task_spec.md",
        limitations="input/limitations.md",
    )

    assert case.case_id == "public_case_1"


def test_task_requirement():
    requirement = TaskRequirement(
        top_design="chip_top",
        test_clocks=["test_clk"],
        scan_enable="scan_en",
    )

    assert requirement.top_design == "chip_top"
    assert requirement.scan_enable == "scan_en"


def test_tool_run_result():
    result = ToolRunResult(
        tool_call_id="R1",
        exit_status=ExitStatus.ERROR,
        log_file="runs/R1/R1.log",
    )

    assert result.tool_call_id == "R1"
    assert result.exit_status == ExitStatus.ERROR