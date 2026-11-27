# Approval-First Agentic Workflow

A local Python workflow agent that turns a bounded request into a validated tool plan, records execution in SQLite, and pauses before a file write until a person approves the exact action.

The project has two planners. The default planner is deterministic and works offline. An optional planner uses the OpenAI Responses API function-calling interface to select a small workflow. Both planners feed the same local validator, allowlisted tools, state store, and approval gate. This is an AI-assisted portfolio project prepared for Ghaya; it does not claim model training or production deployment.

## Capabilities

- Plans a workflow over bundled fictional opportunity examples.
- Lets the optional model choose whether to save a report; the application fixes all tool arguments and report paths.
- Validates tool order, step identifiers, and dependencies before starting a run.
- Reads only the bundled JSON sample and computes its summary locally.
- Stores the plan, step states, results, and audit events in a local SQLite database.
- Pauses before writing and shows the complete report and destination for review.
- Writes only to `reports/opportunities-summary.md`; refuses path changes and replacement of an existing report.
- Runs no shell commands and gives the model no general filesystem, network, or code-execution tool.

## Architecture

```text
Goal
  -> Deterministic planner (default) or optional Responses API planner
  -> Local plan validation and strict tool allowlist
  -> SQLite workflow state and audit events
  -> Read sample -> summarize locally -> [human approval] -> write fixed report
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component map and safety invariants.

## Run offline

Requirements: Python 3.11 or newer. The offline demonstration has no third-party runtime dependencies.

From this directory:

```console
python -m pip install -e .
python -m approval_agent demo
python -m approval_agent pending
python -m approval_agent approve ACTION_ID
```

The demo leaves its final write step pending. Inspect the generated content and destination before approving. The writer will not overwrite an existing report. Start another demonstration only after choosing a new state path or moving the earlier report.

## Use model-assisted planning

Install the optional OpenAI SDK and set `OPENAI_API_KEY` in your operating-system environment. Do not store the key in this repository, a command checked into source control, or the SQLite state file.

```console
python -m pip install -e ".[openai]"
python -m approval_agent run --planner openai --model YOUR_ENABLED_MODEL --allow-model-request --goal "Summarize the example opportunities and prepare a report"
```

The command requires an interactive confirmation: type `SEND` to continue. It sends the goal, fixed planner instructions, and tool schema to OpenAI for planning. The bundled opportunity records stay on the local machine; the application executes their loader and summarizer locally. The Responses API request sets `store=False`. That setting does not itself establish Zero Data Retention; review the provider's current data controls before sending sensitive input. The project stores the goal and workflow results in its local SQLite file without application-level encryption, so use synthetic or non-sensitive goals.

The model can request only the fixed plan-submission function. The application does not execute model-supplied code, arbitrary paths, or arbitrary tool arguments. A report write always requires the separate local `approve` command, regardless of what the model proposes.

## State and limitations

- The default state path is `.agent/state.sqlite3`; use `--state PATH` on any command to choose another local file.
- This is a single-operator demonstration, not a hosted or multi-tenant agent service.
- The sample records are fictional and are not current job listings or completed client work.
- Model planning requires an API key, an account-enabled model, internet access, and may incur API charges. Offline mode remains available.
- No open-source license is included; reuse and redistribution rights have not been granted by this repository.

## API references

- [OpenAI API quickstart](https://developers.openai.com/api/docs/quickstart)
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)

## Attribution

Prepared with AI assistance for Ghaya's portfolio. The project describes its current implementation and limitations; it makes no claim that Ghaya authored every line, trained a model, or deployed a production service.
