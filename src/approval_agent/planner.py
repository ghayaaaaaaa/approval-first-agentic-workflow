from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from .models import Plan, Step


class Planner(Protocol):
    def plan(self, goal: str) -> Plan: ...


class DemoPlanner:
    """Build a fixed, inspectable plan for the bundled opportunity example."""

    def plan(self, goal: str) -> Plan:
        normalized = " ".join(goal.split())
        if not normalized:
            raise ValueError("A non-empty goal is required.")
        if not any(word in normalized.lower() for word in ("summar", "report")):
            raise ValueError(
                "This demonstration planner only handles summaries of its bundled examples."
            )

        return Plan(
            goal=normalized,
            steps=(
                Step(
                    step_id="load-examples",
                    tool="load_sample_opportunities",
                    arguments={},
                ),
                Step(
                    step_id="summarize-examples",
                    tool="summarize_opportunities",
                    arguments={"source": {"$step_result": "load-examples"}},
                ),
                Step(
                    step_id="write-summary",
                    tool="write_summary",
                    arguments={
                        "summary": {"$step_result": "summarize-examples"},
                        "destination": "reports/opportunities-summary.md",
                    },
                    requires_approval=True,
                ),
            ),
        )


_STEP_ID = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_LOAD = "load_sample_opportunities"
_SUMMARIZE = "summarize_opportunities"
_WRITE = "write_summary"
_PLAN_TOOL: dict[str, Any] = {
    "type": "function",
    "name": "submit_workflow_plan",
    "description": (
        "Submit a short, bounded plan for summarizing the bundled fictional "
        "opportunity examples. Use the load step, then the summary step. Add "
        "the report step only when the user asks to save or prepare a report."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_id": {
                            "type": "string",
                            "description": "Short lowercase identifier, such as load-samples.",
                        },
                        "tool": {
                            "type": "string",
                            "enum": [_LOAD, _SUMMARIZE, _WRITE],
                        },
                        "source_step_id": {
                            "type": "string",
                            "description": (
                                "Empty for the loader; otherwise the ID of the "
                                "immediately preceding source step."
                            ),
                        },
                    },
                    "required": ["step_id", "tool", "source_step_id"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["steps"],
        "additionalProperties": False,
    },
    "strict": True,
}

_PLAN_INSTRUCTIONS = """You plan one narrow local workflow over bundled fictional opportunity examples.
Call submit_workflow_plan exactly once. Always use this order:
1. load_sample_opportunities with an empty source_step_id.
2. summarize_opportunities using the step_id from step 1.
3. Include write_summary only if the user asks to save, prepare, or write a report; use the step_id from step 2.
Use two steps when no report is requested and three when it is. Do not add tools, paths, commands, external data, or claims. The application supplies fixed arguments and independently enforces approval before any report write."""


class OpenAIPlanPlanner:
    """Ask the OpenAI Responses API for a bounded plan; execution stays local."""

    def __init__(self, model: str, client: Any | None = None):
        self.model = model.strip()
        if not self.model or len(self.model) > 100:
            raise ValueError("Choose a valid model name.")
        self._client = client

    def plan(self, goal: str) -> Plan:
        normalized = " ".join(goal.split())
        if not normalized:
            raise ValueError("A non-empty goal is required.")
        if not os.environ.get("OPENAI_API_KEY") and self._client is None:
            raise RuntimeError(
                "Set OPENAI_API_KEY in the environment before using the OpenAI planner."
            )

        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "Install the optional dependency with `python -m pip install -e .[openai]`."
                ) from exc
            client = OpenAI()
        else:
            client = self._client

        response = client.responses.create(
            model=self.model,
            instructions=_PLAN_INSTRUCTIONS,
            input=normalized,
            tools=[_PLAN_TOOL],
            tool_choice={"type": "function", "name": "submit_workflow_plan"},
            max_output_tokens=1200,
            store=False,
        )
        if getattr(response, "status", "completed") != "completed":
            raise RuntimeError("The model did not complete its planning response.")

        calls = [
            item
            for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]
        if len(calls) != 1 or getattr(calls[0], "name", None) != "submit_workflow_plan":
            raise ValueError("The model returned an invalid workflow plan.")
        try:
            payload = json.loads(calls[0].arguments)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("The model returned malformed plan arguments.") from exc
        return _validated_plan(normalized, payload)


def _validated_plan(goal: str, payload: Any) -> Plan:
    if not isinstance(payload, dict) or set(payload) != {"steps"}:
        raise ValueError("The plan must contain only a steps array.")
    raw_steps = payload["steps"]
    if not isinstance(raw_steps, list) or len(raw_steps) not in {2, 3}:
        raise ValueError("The plan must contain two steps, or three when a report is requested.")

    tool_sequence = [_LOAD, _SUMMARIZE] + ([_WRITE] if len(raw_steps) == 3 else [])
    steps: list[Step] = []
    seen_ids: set[str] = set()
    for index, (raw, expected_tool) in enumerate(zip(raw_steps, tool_sequence, strict=True)):
        if not isinstance(raw, dict) or set(raw) != {"step_id", "tool", "source_step_id"}:
            raise ValueError("Each plan step must contain only step_id, tool, and source_step_id.")
        step_id = raw["step_id"]
        source_step_id = raw["source_step_id"]
        if not isinstance(step_id, str) or not _STEP_ID.fullmatch(step_id) or step_id in seen_ids:
            raise ValueError("Plan step IDs must be unique, short lowercase identifiers.")
        if raw["tool"] != expected_tool:
            raise ValueError("The plan uses an unknown or out-of-order tool.")
        expected_source = "" if index == 0 else steps[-1].step_id
        if source_step_id != expected_source:
            raise ValueError("Each step must refer only to its immediately preceding source step.")

        arguments: dict[str, Any]
        requires_approval = expected_tool == _WRITE
        if expected_tool == _LOAD:
            arguments = {}
        elif expected_tool == _SUMMARIZE:
            arguments = {"source": {"$step_result": source_step_id}}
        else:
            arguments = {
                "summary": {"$step_result": source_step_id},
                "destination": "reports/opportunities-summary.md",
            }
        steps.append(
            Step(
                step_id=step_id,
                tool=expected_tool,
                arguments=arguments,
                requires_approval=requires_approval,
            )
        )
        seen_ids.add(step_id)

    return Plan(goal=goal, steps=tuple(steps))

