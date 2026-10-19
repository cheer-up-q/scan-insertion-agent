"""Deterministic Task Parser for ``task_spec.md``.

This module converts explicit natural-language DFT requirements into the
shared :class:`~src.contracts.models.TaskRequirement` contract.

The parser follows ``docs/task_requirement_mapping.md``:

* explicit requirements are mapped directly;
* parameters that are not stated stay ``None`` or empty;
* ambiguous requirements are reported through ``unresolved_requirements``;
* values are never guessed from design experience or from a signal name.

The implementation is intentionally rule based.  It does not call an LLM, so
the same input always yields the same output and every decision can be traced
back to a pattern in the task specification.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from src.contracts.models import (
    InternalScanRequirement,
    TaskRequirement,
    WrapperScanRequirement,
)


# ---------------------------------------------------------------------------
# Token and text helpers
# ---------------------------------------------------------------------------

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
_LIST_SEPARATOR_RE = re.compile(r"\s*(?:、|,|，|/|和|与|及|以及|\band\b)\s*")
_SENTENCE_RE = re.compile(r"[。；;\n]+")

# English words that may appear inside a requirement clause but are not
# design-object names.  Signal names such as ``test_clk``, ``scan_en`` or
# ``core0`` are not affected because the match is on the whole token.
_STOPWORDS = frozenset(
    {
        "a",
        "all",
        "an",
        "and",
        "as",
        "be",
        "both",
        "cell",
        "cells",
        "chain",
        "chains",
        "clock",
        "clocks",
        "core",
        "ctl",
        "dft",
        "disable",
        "disabled",
        "domain",
        "domains",
        "each",
        "enable",
        "enabled",
        "external",
        "falling",
        "for",
        "from",
        "generate",
        "in",
        "input",
        "inputs",
        "insertion",
        "internal",
        "is",
        "lockup",
        "mixed",
        "module",
        "need",
        "needs",
        "netlist",
        "of",
        "on",
        "or",
        "output",
        "outputs",
        "per",
        "post",
        "pre",
        "report",
        "reports",
        "require",
        "required",
        "requirement",
        "requirements",
        "reset",
        "resets",
        "rising",
        "scan",
        "scandef",
        "scope",
        "signal",
        "signals",
        "strategy",
        "test",
        "the",
        "to",
        "top",
        "two",
        "use",
        "using",
        "with",
        "wrapper",
    }
)


def _clauses(text: str) -> List[str]:
    """Split a task specification into non-empty sentences."""

    return [part.strip() for part in _SENTENCE_RE.split(text) if part.strip()]


def _parse_names(fragment: Optional[str]) -> List[str]:
    """Extract design-object names from a clause fragment.

    Names are kept in the order in which they appear.  Common English
    keywords are filtered out so that ``clk_a 和 clk_b 两个 Clock Domain``
    becomes ``["clk_a", "clk_b"]``.
    """

    if not fragment:
        return []

    names: List[str] = []
    for part in _LIST_SEPARATOR_RE.split(fragment):
        for token in _IDENTIFIER_RE.findall(part):
            if token.lower() in _STOPWORDS:
                continue
            if token not in names:
                names.append(token)
    return names


def _first_match(patterns: Sequence[re.Pattern], text: str) -> Optional[str]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def _dedupe(items: Iterable[str]) -> List[str]:
    result: List[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Field patterns
# ---------------------------------------------------------------------------

_TOP_DESIGN_PATTERNS = (
    re.compile(
        r"对\s*顶层(?:模块|设计)?\s*[`'\"]?([A-Za-z_][A-Za-z0-9_$]*)[`'\"]?"
        r"\s*(?:执行|进行|完成|做)"
    ),
    re.compile(
        r"(?:顶层(?:模块|设计)?|Top\s*Design)\s*(?:为|是|使用|采用|设置为|设为)"
        r"\s*[`'\"]?([A-Za-z_][A-Za-z0-9_$]*)",
        re.IGNORECASE,
    ),
    re.compile(
        r"对\s*(?:模块|设计)\s*[`'\"]?([A-Za-z_][A-Za-z0-9_$]*)[`'\"]?"
        r"\s*(?:执行|进行|完成)"
    ),
)

_TEST_CLOCK_PATTERNS = (
    re.compile(
        r"(?:测试时钟|测试\s*Clock|Scan\s*Clock)\s*"
        r"(?:为|是|包括|包含|使用|采用|有|设置为|设为)?\s*([^。；;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"使用\s*([A-Za-z_][A-Za-z0-9_$]*(?:\s*(?:、|,|，|和|与|及|以及|and)\s*"
        r"[A-Za-z_][A-Za-z0-9_$]*)*)\s*作为(?:测试时钟|测试\s*Clock|Scan\s*Clock)",
        re.IGNORECASE,
    ),
)

_RESET_PATTERNS = (
    re.compile(
        r"(?:复位信号|复位控制|Reset)\s*"
        r"(?:为|是|包括|包含|使用|采用|有|设置为|设为)?\s*([^。；;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"使用\s*([A-Za-z_][A-Za-z0-9_$]*(?:\s*(?:、|,|，|和|与|及|以及|and)\s*"
        r"[A-Za-z_][A-Za-z0-9_$]*)*)\s*作为(?:复位信号|复位控制|Reset)",
        re.IGNORECASE,
    ),
)

_SCAN_ENABLE_PATTERNS = (
    re.compile(
        r"(?:Scan\s*Enable|扫描使能信号|扫描使能|测试使能)\s*"
        r"(?:为|是|使用|采用|设置为|设为)?\s*[`'\"]?([A-Za-z_][A-Za-z0-9_$]*)",
        re.IGNORECASE,
    ),
    re.compile(
        r"使用\s*[`'\"]?([A-Za-z_][A-Za-z0-9_$]*)[`'\"]?\s*作为\s*"
        r"(?:Scan\s*Enable|扫描使能(?:信号)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"使用\s*[`'\"]?([A-Za-z_][A-Za-z0-9_$]*)[`'\"]?\s*控制\s*"
        r"(?:扫描模式|Scan\s*mode)",
        re.IGNORECASE,
    ),
)

_CHAIN_COUNT_PATTERNS = (
    re.compile(
        r"(?:配置|建立|使用|设置|插入|创建)\s*(\d+)\s*条\s*"
        r"(?:(?:内部|Internal)\s*)?(?:扫描链|Scan\s*Chain)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+)\s*条\s*(?:(?:内部|Internal)\s*)?(?:扫描链|Scan\s*Chain)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:扫描链数量|Scan\s*Chain\s*(?:数量|Count|Number))\s*"
        r"(?:设置|设)?\s*(?:为|是|设置为|设为)?\s*(\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Internal\s*Scan\s*Chain|内部扫描链)\s*数量\s*"
        r"(?:为|是|设置为|设为)?\s*(\d+)",
        re.IGNORECASE,
    ),
)

_CHAIN_LENGTH_EXACT_PATTERNS = (
    re.compile(
        r"每条\s*(?:(?:Scan\s*Chain|扫描链)\s*)?(?:的)?\s*长度\s*"
        r"(?:设置)?\s*(?:为|是)\s*(\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Scan\s*Chain|扫描链)\s*长度\s*(?:设置)?\s*"
        r"(?:为|是|设置为|设为)\s*(\d+)",
        re.IGNORECASE,
    ),
)

_CLOCK_DOMAIN_PATTERNS = (
    re.compile(
        r"(?:扫描设计|Scan\s*设计|设计)\s*(?:包含|包括|涉及|使用|有)\s*"
        r"([^。；;\n]+?)\s*(?:两个|多个)?\s*(?:Clock\s*Domain(?:s)?|时钟域)",
        re.IGNORECASE,
    ),
    re.compile(
        r"Clock\s*Domain(?:s)?\s*(?:为|是|包括|包含)\s*([^。；;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"([A-Za-z_][A-Za-z0-9_$]*(?:\s*(?:、|,|，|和|与|及|以及|and)\s*"
        r"[A-Za-z_][A-Za-z0-9_$]*)+)\s*(?:分别)?\s*(?:建立|划分|属于).{0,10}"
        r"(?:扫描链|Scan\s*Chain)",
        re.IGNORECASE,
    ),
)

_WRAPPER_SCOPE_PATTERNS = (
    re.compile(
        r"Wrapper(?:\s*Scan)?\s*(?:范围|作用范围|Scope)\s*"
        r"(?:为|是|包括|包含|使用)?\s*([^。；;\n]+)",
        re.IGNORECASE,
    ),
)

_WRAPPER_CONTROL_PATTERNS = (
    re.compile(
        r"Wrapper(?:\s*Scan)?\s*(?:控制信号|control\s*signals?)\s*"
        r"(?:为|是|包括|包含|使用)?\s*([^。；;\n]+)",
        re.IGNORECASE,
    ),
)

_WRAPPER_STRATEGY_RE = re.compile(
    r"(?:Wrapper\s*Cell|wrapper_cell)\s*(?:策略|Strategy)\s*"
    r"(?:为|是|使用|采用|设置为|设为)?\s*[`'\"]?([A-Za-z_][A-Za-z0-9_$-]*)",
    re.IGNORECASE,
)

_WRAPPER_ENABLED_RE = re.compile(
    r"(?:启用|开启|使用|需要|要求)\s*(?:Wrapper(?:\s*Scan)?)", re.IGNORECASE
)

_WRAPPER_DISABLED_RE = re.compile(
    r"(?:不启用|不开启|禁用|关闭|无需|不需要)\s*(?:Wrapper(?:\s*Scan)?)",
    re.IGNORECASE,
)

_INTERNAL_DISABLED_RE = re.compile(
    r"(?:不启用|禁用|关闭|不做)\s*(?:内部扫描|Internal\s*Scan|Scan\s*Insertion)",
    re.IGNORECASE,
)

_LOCKUP_REQUIRED_RE = re.compile(
    r"(?:需要|必须|要求|应|要)\s*(?:插入|添加|使用)?\s*Lockup", re.IGNORECASE
)

_LOCKUP_FORBIDDEN_RE = re.compile(
    r"(?:不允许|禁止|不要|无需|不需要|不得)\s*(?:插入|添加|使用)?\s*Lockup",
    re.IGNORECASE,
)

_LOCKUP_STRATEGY_RE = re.compile(
    r"Lockup\s*(?:策略|Strategy)\s*(?:为|是|使用|采用|设置为|设为)?\s*"
    r"[`'\"]?([A-Za-z_][A-Za-z0-9_$-]*)",
    re.IGNORECASE,
)

_OUTPUT_CLAUSE_RE = re.compile(
    r"(?:需要生成|需要输出|需要交付|生成|输出|交付|提供|产出|"
    r"produce|generate|deliver|output)([^。；;\n]*)",
    re.IGNORECASE,
)

_OUTPUT_TERMS: Tuple[Tuple[str, re.Pattern], ...] = (
    (
        "post_scan_netlist",
        re.compile(r"post[\s_-]*scan\s*netlist|扫描后网表|后扫描网表", re.IGNORECASE),
    ),
    ("ctl", re.compile(r"\bCTL\b", re.IGNORECASE)),
    ("scandef", re.compile(r"\bSCANDEF\b|Scan\s*Def", re.IGNORECASE)),
    ("scan_report", re.compile(r"Scan\s*Report|扫描报告", re.IGNORECASE)),
    ("dft_report", re.compile(r"DFT\s*Report|DFT\s*报告", re.IGNORECASE)),
    ("wrapper_report", re.compile(r"Wrapper\s*Report|Wrapper\s*报告", re.IGNORECASE)),
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TaskParser:
    """Convert ``task_spec.md`` text into a :class:`TaskRequirement`.

    The class exposes a small, stable interface for the A/B integration:

    ``parse(task_spec, limitations=None) -> TaskRequirement``
        Parse an in-memory task specification.

    ``parse_file(task_spec_path, limitations_path=None) -> TaskRequirement``
        Read a task specification from disk and parse it.
    """

    def parse(
        self, task_spec: str, limitations: Optional[str] = None
    ) -> TaskRequirement:
        """Parse a task specification.

        Parameters
        ----------
        task_spec:
            Contents of ``task_spec.md``.
        limitations:
            Optional contents of ``limitations.md``.  When supplied, explicit
            conflicts between the two inputs are recorded in
            ``unresolved_requirements`` instead of silently overriding either
            side.

        Returns
        -------
        TaskRequirement
            A model instance that has already passed Pydantic validation.
        """

        if task_spec is None:
            raise ValueError("task_spec must not be None")
        text = task_spec.strip()
        if not text:
            raise ValueError("task_spec must not be empty")

        unresolved: List[str] = []

        top_design = self._parse_top_design(text, unresolved)
        test_clocks = self._parse_test_clocks(text, unresolved)
        resets = self._parse_resets(text, unresolved)
        scan_enable = self._parse_scan_enable(text, unresolved)

        chain_count = self._parse_chain_count(text, unresolved)
        chain_length = self._parse_chain_length(text, unresolved)
        clock_domains = self._parse_clock_domains(text, unresolved)
        edge_strategy = self._parse_edge_strategy(text, unresolved)
        lockup_required, lockup_strategy = self._parse_lockup(text)
        wrapper_scan = self._parse_wrapper_scan(text, unresolved)
        output_requirements = self._parse_output_requirements(text)

        if limitations:
            self._check_conflicts(
                limitations,
                scan_enable=scan_enable,
                test_clocks=test_clocks,
                resets=resets,
                unresolved=unresolved,
            )

        return TaskRequirement(
            top_design=top_design,
            test_clocks=test_clocks,
            resets=resets,
            scan_enable=scan_enable,
            internal_scan=InternalScanRequirement(
                enabled=not bool(_INTERNAL_DISABLED_RE.search(text)),
                chain_count=chain_count,
                chain_length=chain_length,
                clock_domains=clock_domains,
                edge_strategy=edge_strategy,
                lockup_required=lockup_required,
                lockup_strategy=lockup_strategy,
            ),
            wrapper_scan=wrapper_scan,
            output_requirements=output_requirements,
            unresolved_requirements=_dedupe(unresolved),
        )

    def parse_file(
        self,
        task_spec_path: str,
        limitations_path: Optional[str] = None,
    ) -> TaskRequirement:
        """Parse a task specification from a file."""

        task_spec = Path(task_spec_path).read_text(encoding="utf-8")
        limitations = None
        if limitations_path:
            limitations = Path(limitations_path).read_text(encoding="utf-8")
        return self.parse(task_spec, limitations=limitations)

    # -- individual fields -------------------------------------------------

    def _parse_top_design(self, text: str, unresolved: List[str]) -> Optional[str]:
        top_design = _first_match(_TOP_DESIGN_PATTERNS, text)
        if not top_design and re.search(
            r"(?:当前设计|current\s+design|顶层(?:模块|设计)?)", text, re.IGNORECASE
        ):
            unresolved.append("Top design must be determined from design analysis.")
        return top_design

    def _parse_test_clocks(self, text: str, unresolved: List[str]) -> List[str]:
        fragment = _first_match(_TEST_CLOCK_PATTERNS, text)
        clocks = _parse_names(fragment)
        if not clocks and re.search(
            r"(?:测试时钟|测试\s*Clock|Scan\s*Clock|design\s+test\s+clock)",
            text,
            re.IGNORECASE,
        ):
            unresolved.append("Test clock must be determined from design analysis.")
        return clocks

    def _parse_resets(self, text: str, unresolved: List[str]) -> List[str]:
        fragment = _first_match(_RESET_PATTERNS, text)
        resets = _parse_names(fragment)
        if not resets and re.search(r"(?:复位|Reset)", text, re.IGNORECASE):
            unresolved.append("Reset signal must be identified from the design.")
        return resets

    def _parse_scan_enable(self, text: str, unresolved: List[str]) -> Optional[str]:
        scan_enable = _first_match(_SCAN_ENABLE_PATTERNS, text)
        if not scan_enable and re.search(
            r"(?:Scan\s*Enable|扫描使能)", text, re.IGNORECASE
        ):
            unresolved.append(
                "Scan enable signal must be identified from the design."
            )
        return scan_enable

    def _parse_chain_count(self, text: str, unresolved: List[str]) -> Optional[int]:
        for pattern in _CHAIN_COUNT_PATTERNS:
            match = pattern.search(text)
            if match:
                return int(match.group(1))

        if re.search(
            r"(?:尽量|尽可能|合理|适当|减少|最小|至少|最多)[^。；;\n]{0,12}"
            r"(?:扫描链|Scan\s*Chain)[^。；;\n]{0,12}(?:数量|Count|Number)"
            r"|(?:扫描链数量|Scan\s*Chain\s*(?:数量|Count|Number))",
            text,
            re.IGNORECASE,
        ):
            unresolved.append("Scan chain count is not explicitly specified.")
        return None

    def _parse_chain_length(
        self, text: str, unresolved: List[str]
    ) -> Optional[int]:
        length_clauses = [
            clause
            for clause in _clauses(text)
            if re.search(r"(?:长度|length)", clause, re.IGNORECASE)
        ]

        for clause in length_clauses:
            if re.search(r"(?:最大|最小|不超过|以内|以下|至少|最多|上限|下限)", clause):
                unresolved.append(
                    "Maximum scan chain length constraint cannot be represented "
                    "unambiguously by the current chain_length field."
                )
                return None
            if re.search(r"(?:均衡|平衡)", clause):
                unresolved.append(
                    "Scan chain balancing requirement requires later "
                    "configuration or tool analysis."
                )
                return None
            if re.search(r"(?:目标|推荐)", clause):
                unresolved.append(
                    "Scan chain length target or recommendation cannot be "
                    "represented unambiguously by the current chain_length field."
                )
                return None
            if re.search(r"(?:合理|适当)", clause):
                unresolved.append("Scan chain length is not explicitly specified.")
                return None

        for pattern in _CHAIN_LENGTH_EXACT_PATTERNS:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        return None

    def _parse_clock_domains(self, text: str, unresolved: List[str]) -> List[str]:
        fragment = _first_match(_CLOCK_DOMAIN_PATTERNS, text)
        domains = _parse_names(fragment)

        if not domains and re.search(
            r"(?:Clock\s*Domain|时钟域)", text, re.IGNORECASE
        ):
            unresolved.append(
                "Clock domains must be determined from design analysis."
            )

        if re.search(
            r"(?:禁止|不得|不允许)[^。；;\n]{0,10}(?:混链|混合|混在)",
            text,
            re.IGNORECASE,
        ):
            unresolved.append(
                "Clock-domain chain separation policy requires additional "
                "configuration semantics."
            )
        return domains

    def _parse_edge_strategy(
        self, text: str, unresolved: List[str]
    ) -> Optional[str]:
        has_rising = bool(re.search(r"上升沿|rising|posedge", text, re.IGNORECASE))
        has_falling = bool(
            re.search(r"下降沿|falling|negedge", text, re.IGNORECASE)
        )
        explicit_mixed = bool(
            re.search(r"(?:混合边沿|混合触发|mixed\s*edge|edge\s*strategy\s*[:=]\s*mixed)", text, re.IGNORECASE)
        )

        if re.search(
            r"(?:不同|各|每个|per[- ]?domain|domain[- ]specific)"
            r"[^。；;\n]{0,20}(?:边沿|edge)",
            text,
            re.IGNORECASE,
        ):
            unresolved.append(
                "Domain-specific edge strategy requires additional "
                "configuration semantics."
            )

        if explicit_mixed or (has_rising and has_falling):
            return "mixed"
        if has_rising:
            return "rising"
        if has_falling:
            return "falling"
        return None

    def _parse_lockup(self, text: str) -> Tuple[Optional[bool], Optional[str]]:
        required: Optional[bool] = None
        for clause in _clauses(text):
            if _LOCKUP_FORBIDDEN_RE.search(clause):
                required = False
            elif required is None and _LOCKUP_REQUIRED_RE.search(clause):
                required = True

        strategy_match = _LOCKUP_STRATEGY_RE.search(text)
        strategy = strategy_match.group(1) if strategy_match else None
        if strategy and required is None:
            required = True
        return required, strategy

    def _parse_wrapper_scan(
        self, text: str, unresolved: List[str]
    ) -> WrapperScanRequirement:
        enabled = False
        if _WRAPPER_DISABLED_RE.search(text):
            enabled = False
        elif _WRAPPER_ENABLED_RE.search(text):
            enabled = True

        scope_fragment = _first_match(_WRAPPER_SCOPE_PATTERNS, text)
        scope = _parse_names(scope_fragment)
        control_fragment = _first_match(_WRAPPER_CONTROL_PATTERNS, text)
        control_signals = _parse_names(control_fragment)

        strategy_match = _WRAPPER_STRATEGY_RE.search(text)
        strategy = strategy_match.group(1) if strategy_match else None

        if scope or control_signals or strategy:
            enabled = True

        if enabled and not scope:
            unresolved.append(
                "Wrapper scope must be determined from design analysis."
            )

        return WrapperScanRequirement(
            enabled=enabled,
            scope=scope,
            control_signals=control_signals,
            wrapper_cell_strategy=strategy,
        )

    def _parse_output_requirements(self, text: str) -> List[str]:
        outputs: List[str] = []
        for clause_match in _OUTPUT_CLAUSE_RE.finditer(text):
            clause = clause_match.group(1)
            matches: List[Tuple[int, str]] = []
            for name, pattern in _OUTPUT_TERMS:
                for match in pattern.finditer(clause):
                    matches.append((match.start(), name))
            for _, name in sorted(matches):
                if name not in outputs:
                    outputs.append(name)
        return outputs

    def _check_conflicts(
        self,
        limitations: str,
        scan_enable: Optional[str],
        test_clocks: Sequence[str],
        resets: Sequence[str],
        unresolved: List[str],
    ) -> None:
        fields: List[Tuple[str, Sequence[str]]] = []
        if scan_enable:
            fields.append(("scan_enable", [scan_enable]))
        if test_clocks:
            fields.append(("test_clocks", test_clocks))
        if resets:
            fields.append(("resets", resets))

        for field, names in fields:
            if any(_is_forbidden(limitations, name) for name in names):
                unresolved.append(
                    "Conflict detected between task_spec.md and limitations.md "
                    f"for {field}."
                )


def _is_forbidden(limitations: str, name: str) -> bool:
    """Return whether ``limitations`` explicitly forbids using ``name``.

    A statement such as ``禁止修改 scan_en 信号定义`` is a constraint on
    modification, not a prohibition on using the signal, so it must not be
    reported as a conflict.
    """

    escaped = re.escape(name)
    patterns = (
        rf"(?:禁止|不得|不允许|不可|严禁)[^。；;\n]{{0,20}}"
        rf"(?:使用|采用|将|把)[^。；;\n]{{0,12}}{escaped}(?![A-Za-z0-9_$])",
        rf"(?:do\s+not|must\s+not|forbid(?:den)?)[^.;\n]{{0,20}}"
        rf"(?:use\s+)?{escaped}(?![A-Za-z0-9_$])",
    )
    return any(re.search(pattern, limitations, re.IGNORECASE) for pattern in patterns)


def parse_task_spec(
    task_spec: str, limitations: Optional[str] = None
) -> TaskRequirement:
    """Convenience wrapper around :meth:`TaskParser.parse`."""

    return TaskParser().parse(task_spec, limitations=limitations)


def parse_file(
    task_spec_path: str, limitations_path: Optional[str] = None
) -> TaskRequirement:
    """Convenience wrapper around :meth:`TaskParser.parse_file`."""

    return TaskParser().parse_file(task_spec_path, limitations_path)


def to_json(requirement: TaskRequirement, indent: int = 2) -> str:
    """Serialize a requirement to stable UTF-8 JSON text."""

    if hasattr(requirement, "model_dump"):
        payload = requirement.model_dump()
    else:  # pragma: no cover - Pydantic v1 compatibility
        payload = requirement.dict()
    return json.dumps(payload, ensure_ascii=False, indent=indent)
