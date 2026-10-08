# Agent skills

[README](../README.md) · [How it works](../docs/HOW_IT_WORKS.md) · [AGENTS.md](../AGENTS.md)

Two skills for the **developer's coding agent** (for example Antigravity or Gemini CLI), not for the Trend Signals
agent itself. Each skill is a folder with a `SKILL.md` and supporting files, in the open Agent Skills format
(https://agentskills.io/specification).

| Skill | Use it for |
|---|---|
| [`ge-agentic-workspace`](ge-agentic-workspace/SKILL.md) | Building or adapting an agent-driven workspace like this one: a custom page in the Canvas side panel that shares state with an ADK agent. Uses this repository as the reference implementation. |
| [`gemini-enterprise-a2ui`](gemini-enterprise-a2ui/SKILL.md) | A2UI v0.9 for Gemini Enterprise in general: components and properties, data binding and forms, actions and prompts, Canvas and `IFrameSrcdoc`, suggestions, grounding display, agent registration and API testing, with an offline validator |

| File | Contents |
|---|---|
| [ge-agentic-workspace/SKILL.md](ge-agentic-workspace/SKILL.md) | The workspace design, the rules that shape it, styling, and a recipe for a new workspace from this one |
| [gemini-enterprise-a2ui/SKILL.md](gemini-enterprise-a2ui/SKILL.md) | Catalog and agent card, messages, rules, verified rendering behavior, recipes, troubleshooting |
| [gemini-enterprise-a2ui/references/](gemini-enterprise-a2ui/references/) | Component catalog, functions and styling, message blueprints and agent integration, theming, the agentic workspace |
| [gemini-enterprise-a2ui/scripts/validate_a2ui.py](gemini-enterprise-a2ui/scripts/validate_a2ui.py) | Offline validator: catalog schemas, tree rules and rendering warnings |
| [gemini-enterprise-a2ui/resources/](gemini-enterprise-a2ui/resources/) | The published composite catalog the validator reads |

## Install

In this repository, Antigravity loads both skills automatically: `.agents/skills.json` registers `skills/`. To use
them in another project, copy the folders into that project's skills directory, or register them the same way:

```bash
mkdir -p .agents && echo '{"entries":[{"path":"skills"}]}' > .agents/skills.json   # Antigravity
mkdir -p .agents/skills && ln -s ../../skills/ge-agentic-workspace .agents/skills/  # Gemini CLI
```

Ask the agent "Which skills do you have?" to check; the answer includes both names.

## Example prompts

| Task | Try |
|---|---|
| New data | "Replace the illustrative catalog with rows from a BigQuery table and keep the workspace working" |
| New view | "Add a view that shows trends by region as a small-multiples chart, and let the agent open it" |
| New tool | "Add a tool that flags trends whose forecast fell this week and highlights them on the map" |
| Layout | "The workspace is cut off in the Canvas. Why, and how is the frame sized?" |
| Latency | "Gemini Enterprise says the connection to the server was lost. What limits apply?" |
| A2UI payload | "Gemini Enterprise shows 'Couldn't display this content' for this payload. Find the problem" |

## Validate payloads

```bash
python3 skills/gemini-enterprise-a2ui/scripts/validate_a2ui.py payload.json
cat payload.json | python3 skills/gemini-enterprise-a2ui/scripts/validate_a2ui.py - --strict
```

Errors mean Gemini Enterprise would reject the surface; warnings mean it renders differently than the schema
suggests. `make test` also validates every surface the agent builds against the same catalog.
