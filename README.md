# Approval-First Agentic Workflow

A small, local workflow agent that plans a bounded task, calls allowlisted tools, records each transition in SQLite, and pauses before a file-writing action until a person approves it.


## What it does

- Converts a narrow request into a three-step plan.
- Reads only the bundled, synthetic opportunity examples.
- Produces a compact summary from those examples.
- Requires a separate approval command before writing a Markdown report.
- Stores plans, step states, results, and audit events in a local SQLite database.
- Refuses unknown tools and file paths outside the project report directory.
- Does not make network requests or execute shell commands.

## Run the demonstration

Use Python 3.11 or newer. There are no third-party runtime dependencies.

From this directory:

    python -m pip install -e .
    python -m approval_agent demo

The command prints an action ID and leaves the final report step waiting for approval. Inspect the exact report and destination with:

    python -m approval_agent pending

To approve an action, run:

    python -m approval_agent approve ACTION_ID

The command displays the same action preview and requires you to type `approve`. The report writer refuses to replace an existing file; rename or remove the previous demo report before starting another write.

The approved report is written under `reports/`. The local database is stored under `.agent/` and is ignored by Git.

To start a new run:

    python -m approval_agent run --goal "Summarize the bundled opportunities and prepare a report"

Use `--state PATH` with any command to choose a different local SQLite file.


