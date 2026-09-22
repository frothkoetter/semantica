---
title: "MCP Server"
description: "Connect Semantica's knowledge graph, decision intelligence, and reasoning to Claude Desktop, Windsurf, VS Code, Cline, and any MCP-compatible AI client."
icon: "plug"
---

## What Is MCP?

MCP stands for the Model Context Protocol. It is an open standard that allows external AI assistants (like Claude Desktop, Cursor, or Windsurf) to securely access local tools and data sources. 

The Semantica MCP server exposes your knowledge graph as 17 callable tools. By connecting it, any compatible AI client can traverse the graph live, record decisions, run analytics, import ontologies, and export results during a conversation — without you having to write custom tool wrappers.

<Info>
  The Semantica MCP server exposes 14 tools and 3 read-only resources. All tools accept and return JSON. Optional env vars: `SEMANTICA_KG_PATH` (persisted graph), `SEMANTICA_MAPPING_CONFIG` (ontology↔DB mapping YAML). Hive/Iceberg SQL and schema introspection use **iceberg-mcp-server-hive**, not Semantica.
</Info>

## Architecture & Communication

It is important to understand how MCP works under the hood. **The Semantica MCP server is not a REST API.** There are no network ports, no HTTP endpoints, and no API keys required.

Instead, the AI client launches `semantica-mcp` locally as a subprocess. All communication between the AI and Semantica happens securely through standard input and output (`stdio`). Because the server runs locally under your user account, it inherently has your local file permissions.

## Why Use MCP With Semantica?

- **Zero-Code Integration**: Instantly connect Semantica's graph capabilities to your favorite AI IDE or desktop chat app without writing any glue code.
- **Real-Time Graph Updates**: Chat with an AI to extract entities from documents and watch them populate your live knowledge graph instantly.
- **Auditable AI**: Use the AI to make decisions and have it automatically record the reasoning and causal chain directly into the graph via Semantica's decision intelligence tools.

## When To Use / When Not To Use

- **When to Use**: You want to use a third-party AI interface (like Claude Desktop or Windsurf) to manipulate, query, and reason over a Semantica knowledge graph on your local machine.
- **When NOT to Use**: You are building an autonomous Python script or backend service. If you are writing Python code to build an agent, use `semantica.context.AgentContext` natively instead of spinning up an MCP server. The MCP server does not support remote hosting over HTTP/SSE.

---

## Typical Workflow

Connecting your AI client follows a standard progression:

1. **Install**: Install Semantica in your Python environment.
2. **Configure Client**: Add the `semantica-mcp` command and absolute graph paths to your AI client's JSON configuration.
3. **Start Client**: Launch Claude Desktop or Windsurf, which automatically spawns the MCP server.
4. **Tool Calls**: Prompt the AI in natural language. The AI autonomously chains the 12 available tools.
5. **Graph Updates**: The AI directly modifies your local graph, adding entities, edges, and decisions.

---

## Starting the Server

Install Semantica, then configure your client to launch the MCP server. The server runs using the `stdio` transport.

```bash
pip install semantica
```

```bash
# Via the CLI entry-point (recommended)
semantica-mcp

# Or via the Python module directly
python -m semantica.mcp_server
```

By default, the server logs at `WARNING` level and produces no startup output. Set `SEMANTICA_LOG_LEVEL=INFO` (or `DEBUG`) to see startup messages on stderr. Without `SEMANTICA_KG_PATH` the server initialises an empty in-memory graph — sufficient for testing. For a persistent graph that survives restarts, set the path:

```bash
SEMANTICA_KG_PATH=/data/threat_graph.json semantica-mcp
```

<Info>
  Without `SEMANTICA_KG_PATH`, the graph resets when the server process exits. Always set this path using an absolute file path for any session whose data should survive a restart.
</Info>

## Connecting to Claude Desktop

Edit the Claude Desktop config file — on macOS at `~/Library/Application Support/Claude/claude_desktop_config.json`, on Windows at `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "semantica": {
      "command": "semantica-mcp",
      "env": {
        "SEMANTICA_KG_PATH": "/absolute/path/to/knowledge_graph.json",
        "SEMANTICA_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Restart Claude Desktop after saving. The Semantica tools appear in the tool palette automatically — Claude can now call them during any conversation.

If `semantica-mcp` is not on your system PATH (for example, if it is installed in a virtualenv), use the full absolute binary path in `"command"`: `"/path/to/venv/bin/semantica-mcp"`.

## Connecting to Other Clients

**Windsurf** — in Settings → MCP Servers → Add Server, or edit `~/.windsurf/mcp_servers.json`:

```json
{
  "semantica": {
    "command": "semantica-mcp",
    "env": { "SEMANTICA_KG_PATH": "/absolute/path/to/knowledge_graph.json" }
  }
}
```

**VS Code (Cline / Roo Code / Continue)** — add to `.mcp.json` in your project root:

```json
{
  "servers": {
    "semantica": {
      "type": "stdio",
      "command": "semantica-mcp",
      "env": {
        "SEMANTICA_KG_PATH": "${workspaceFolder}/knowledge_graph.json",
        "SEMANTICA_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

**Docker**:

```bash
docker run --rm -i \
  -e SEMANTICA_KG_PATH=/data/kg.json \
  -v /local/absolute/path:/data \
  ghcr.io/semantica-agi/semantica-mcp:latest
```

## What the Agent Can Do: The 14 Tools

Once connected, the LLM can call any of these tools during a conversation. The agent chains them automatically — you do not orchestrate the sequence, you just describe what you want.

**Entity and relation extraction** — `extract_entities` pulls named entities from free text; `extract_relations` extracts semantic relationships and RDF triplets. These two tools turn a raw OSINT report into structured graph inputs without any preprocessing.

**Knowledge graph manipulation** — `add_entity` adds a node, `add_relationship` adds a directed edge. After extraction, the agent calls these to persist what it found into the live graph.

**Ontology import (OWL)** — `import_ontology` loads any local OWL/TTL/RDF file or download URL into the graph as `OntologyClass` and property nodes. `map_db_schema_to_ontology` maps tables/columns to ontology classes using `schema_info` from **iceberg-mcp** `get_database_schema_info` (or a SQL connection string) plus mapping YAML (`mapping_config_path` or `SEMANTICA_MAPPING_CONFIG`).

**Decision intelligence** — `record_decision` writes a decision as a provenance node with confidence score, reasoning, and decision maker identity. `query_decisions` retrieves past decisions by query or category. `find_precedents` finds the most similar past decisions by semantic similarity. `get_causal_chain` traces decision causality upstream or downstream.

**Reasoning** — `run_reasoning` applies forward-chaining IF/THEN rules over a set of facts and returns derived conclusions.

**Analytics and export** — `get_graph_analytics` computes PageRank centrality and community detection. `get_graph_summary` returns node counts, ontology class names, database table mappings, and `SEMANTICA_KG_PATH` status. `export_graph` serializes the current graph to Turtle (`"turtle"` / `"ttl"`), RDF/XML (`"xml"`), N-Triples (`"nt"`), JSON-LD (`"json-ld"`), or plain JSON (`"json"`).

## Ontology + Database Mapping Workflow

For any domain ontology, chain these tools:

```text
1. import_ontology(file_path="/path/to/ontology.ttl")
   → loads OntologyClass and property nodes

2. map_db_schema_to_ontology(
       connection_string="postgresql://user:pass@localhost/mydb",
       mapping_config_path="config/my_domain_mapping.yaml",
       apply_mappings=true
   )
   → maps DB tables/columns using explicit YAML rules

3. get_graph_summary()
   export_graph(format="turtle")
```

### Customizing table/column mappings

Edit `config/airline_r2rml_db_mapping.yaml` (or pass `mapping_config_path` to the tool):

```yaml
ontology_namespace: "https://w3id.org/demo/airline#"

tables:
  flights: Flight
  airlines: Airline

columns:
  _global:
    arrdelay: arrDelay
    year: year
```

Table and column keys are normalized (lowercase, no underscores, umlauts → `ae`/`oe`/`ue`).

Build the graph with mappings applied:

```bash
uv run python scripts/build_airline_graph.py
```

### Iceberg / Hive (CDW) integration

When tables live on Cloudera Iceberg via Hive, chain **two MCP servers**:

```text
# iceberg-mcp-server-hive (HIVE_* env here only)
schema = get_database_schema_info({ "database": "airlinedata" })

# semantica-mcp (no HIVE_* env)
map_db_schema_to_ontology({
  "schema_info": schema.schema_info,
  "mapping_config_path": "config/airline_r2rml_db_mapping.yaml",
  "apply_mappings": true
})
```

For graph builds without MCP, use `scripts/build_airline_graph.py` (internal Hive helpers).

See `deploy/iceberg/README.md` for table DDL and provisioning.

## Universal Example: Employee Directory

Before diving into complex domain examples, here is a simple, universally understood session. An HR manager types a prompt into Claude Desktop:

> "Extract entities from this meeting transcript about Alice transferring to Engineering, add them to the graph, and record a promotion decision."

Claude chains four tool calls automatically:

```text
1. extract_entities(text="Alice is transferring to Engineering...")
   → { "entities": [{"label": "Alice", "type": "Employee"}, {"label": "Engineering", "type": "Department"}] }

2. add_entity(id="emp-alice", label="Alice", type="Employee")
   add_entity(id="dept-eng", label="Engineering", type="Department")

3. add_relationship(source="emp-alice", target="dept-eng", type="WORKS_IN")

4. record_decision(
       category="promotion",
       scenario="Alice transferring to Engineering",
       reasoning="Approved by Engineering Director",
       outcome="transfer_approved",
       confidence=1.0
   )
```
The graph is updated instantly with the new organizational structure and a fully auditable decision trail.

## Watching a Real Agent Session

Here is what happens when a cybersecurity analyst types a prompt into Claude Desktop and the graph is live. The prompt is:

> "Extract entities and relationships from this OSINT report, add them to the knowledge graph, then record an attribution decision for APT29 with confidence 0.88 and export the full graph as Turtle."

Claude chains six tool calls automatically:

```text
1. extract_entities(text="<report text>")
   → { "entities": [{"label": "APT29", "type": "ThreatActor"}, ...] }

2. extract_relations(text="<report text>")
   → { "relations": [{"source": "APT29", "type": "EXPLOITS", "target": "CVE-2024-3400"}] }

3. add_entity(id="apt29", label="APT29", type="ThreatActor", metadata={"alias": "NOBELIUM"})
   → { "status": "added", "id": "apt29" }
   (repeated for each extracted entity)

4. add_relationship(source="apt29", target="cve-2024-3400", type="EXPLOITS",
                    metadata={"confidence": 0.97})
   → { "status": "added" }
   (repeated for each extracted relation)

5. record_decision(
       category="threat_attribution",
       scenario="C2 beacon from 185.220.101.47, TTP T1566.001 observed",
       reasoning="IP overlaps APT29 infrastructure cluster; TTPs match NOBELIUM phishing playbook",
       outcome="attributed_to_apt29",
       confidence=0.88,
       decision_maker="analyst_zhang"
   )
   → { "decision_id": "dec_a3f2b1", "status": "recorded" }

6. export_graph(format="turtle")
   → { "format": "turtle", "data": "@prefix ... <apt29> a :ThreatActor ..." }
```

The analyst asked one question in natural language. Six structured tool calls happened against live graph data. The result is a populated graph, a recorded attribution decision with full provenance, and a Turtle export ready for the SPARQL endpoint — all in a single conversation turn.

## The Three Read-Only Resources

Resources expose graph state without a tool call — the client can read them at any point:

| URI | Description |
| :-- | :---------- |
| `semantica://graph/summary` | Node count, decision count, server status |
| `semantica://decisions/list` | Up to 50 most recent recorded decisions |
| `semantica://schema/info` | Server version, capabilities, available tool list |

## Domain Examples

<Tabs>

<Tab title="Defense — CTI/Threat">

The CTI team uses Claude Desktop to correlate new OSINT reports against the existing threat graph, record attribution decisions, and query causal chains — all through natural language, with the graph updated live.

**Analyst prompt:**
> "Extract entities from this Mandiant report on APT40, add them to the knowledge graph, find any past decisions about APT40 attribution, and record a new attribution decision with confidence 0.84."

Claude chains automatically:

1. `extract_entities` + `extract_relations` on the report text
2. `add_entity` for each extracted entity (APT40, CVEs, infrastructure nodes)
3. `add_relationship` for each extracted relation
4. `query_decisions(query="APT40 attribution", category="threat_attribution")`
5. `find_precedents(scenario="APT40 targeting maritime sector", max_results=3)`
6. `record_decision(category="threat_attribution", outcome="attributed_to_apt40", confidence=0.84, decision_maker="analyst_zhang")`

The attribution is now a graph node linked to the OSINT evidence, searchable by future agents.

```json
{
  "category": "threat_attribution",
  "scenario": "C2 infrastructure overlaps APT40 cluster; TEMP.Periscope TTPs confirmed",
  "reasoning": "Three C2 IPs match known APT40 hosting ASN; T1190 exploit chain identical to 2023 campaign",
  "outcome": "attributed_to_apt40",
  "confidence": 0.84,
  "decision_maker": "analyst_zhang"
}
```

</Tab>

<Tab title="Security — SOC/Incident">

During a live incident, the SOC uses Claude to reason over the graph, apply zero-trust policy rules, and record containment decisions with their causal chain — creating a real-time audit trail.

**SOC analyst prompt:**
> "Add WKSTN-047 and DC01 as hosts, add the lateral movement relationship between them, run reasoning to classify the severity, and record a containment decision."

Claude chains:

1. `add_entity(id="wkstn-047", type="Host", label="WKSTN-047")`
2. `add_entity(id="dc01", type="Host", label="DC01")`
3. `add_relationship(source="wkstn-047", target="dc01", type="lateral_movement")`
4. `run_reasoning(facts=["Host(WKSTN-047)", "LateralMove(WKSTN-047, DC01)", "DC(DC01)"], rules=["IF LateralMove(X, Y) AND DC(Y) THEN CriticalIncident(X)"])`
5. `record_decision(category="containment", scenario="Lateral movement to DC detected", outcome="isolate_wkstn047", confidence=0.95)`
6. `get_causal_chain(decision_id="...", direction="downstream", max_depth=3)`

The containment decision and its downstream effects are captured in the graph for the post-mortem.

</Tab>

<Tab title="Life Science — Clinical/Pharma">

Clinical AI assistants use the MCP server to record treatment decisions with provenance, retrieve guideline precedents, and export decision graphs for regulatory submission and MDT review.

**Clinical prompt:**
> "The patient has eGFR 28 and is on metformin. Find precedents for metformin dose modification with severely reduced kidney function, then record a treatment modification decision."

Claude calls:

1. `find_precedents(scenario="metformin with eGFR below 30", max_results=5)`
2. `record_decision(category="treatment_modification", scenario="eGFR 28, current metformin 1000mg BD", reasoning="eGFR 28 is below the 30 mL/min/1.73m2 absolute contraindication threshold per BNF and NICE NG28", outcome="discontinue_metformin_switch_to_gliclazide", confidence=0.97, decision_maker="clinical_ai_v2")`
3. `get_causal_chain(direction="upstream")` — surfaces the guideline node that drove the decision
4. `export_graph(format="json-ld")` — produces the decision graph for MDT review

The graph captures the decision, its guideline basis, and the causal chain — all retrievable for regulatory audit.

</Tab>

<Tab title="Banking — Risk/Compliance">

Credit risk teams use the MCP server to record every lending decision with its reasoning chain, surface regulatory precedents, and export compliance graphs for Basel III model governance review.

**Credit analyst prompt:**
> "Record a conditional mortgage approval for APP-2025-994421 (LTV 78%, DSTI 38%, credit score 714), find the three most similar past approvals, and return the causal chain for this decision."

Claude calls:

1. `record_decision(category="mortgage_origination", scenario="LTV 78%, DSTI 38%, credit score 714, first-time buyer", reasoning="LTV within 80% cap; DSTI 38% under stressed rate scenario breaches 35% guideline — conditional approval with LMI requirement", outcome="approved_conditional_lmi", confidence=0.89, decision_maker="credit_model_v3")`
2. `find_precedents(scenario="mortgage approval borderline DSTI stress test", max_results=3)`
3. `get_causal_chain(decision_id="...", direction="upstream", max_depth=5)`
4. `export_graph(format="turtle")` — produces the decision provenance graph for model governance committee

The result is a fully auditable credit decision trail with precedent links, ready for SR 11-7 model risk governance review.

</Tab>

</Tabs>

---

## Common Pitfalls

- **Treating MCP as an HTTP server**: Do not try to `curl` the MCP server or look for a port number. It communicates via `stdin/stdout` and waits for JSON-RPC messages from the parent AI client.
- **Using relative paths for `SEMANTICA_KG_PATH`**: Because the AI client spawns the server as a subprocess, the working directory can be unpredictable. Always use absolute paths (e.g., `C:\Users\Name\graph.json` or `/Users/name/graph.json`) to avoid losing your data.
- **Virtual environment PATH issues**: If you installed Semantica inside a Python virtual environment, Claude Desktop will not automatically find `semantica-mcp` on the global system PATH. You must provide the absolute path to the binary in the `"command"` field.
- **Expecting remote hosting support**: Stdio-based MCP servers must run on the same local machine as the AI client. Remote execution over a network is not supported.
- **Confusing MCP integration with `AgentContext`**: If you are writing your own Python code to orchestrate an LLM, do not use the MCP server. Use the `AgentContext` class natively within your code.

---

## Troubleshooting

**Server does not appear in Claude Desktop** — fully quit and reopen Claude Desktop after editing the config (closing the window is not enough). Verify the binary is on PATH: `which semantica-mcp` on Unix, `where semantica-mcp` on Windows. If using a virtualenv, use the absolute binary path in `"command"`. Set `SEMANTICA_LOG_LEVEL=DEBUG` and check stderr for startup errors.

**Graph data not persisting between sessions** — set `SEMANTICA_KG_PATH` to an absolute file path. Without it, the graph is in-memory only and resets on every server restart.

**Tool calls returning empty results** — `get_graph_summary` returning `"node_count": 0` means the graph is empty. Populate it via `add_entity` and `add_relationship`, or run `extract_entities` on text first and then `add_entity` for each result.

**Permission errors on `SEMANTICA_KG_PATH`** — the server process needs read/write access to the file and its parent directory. If running inside Docker, verify the volume mount and file ownership.

### Ontology and mapping files fail to load

The MCP server reads configuration from environment variables in your client JSON (`claude_desktop_config.json`, `.cursor/mcp.json`, Agent Studio registration, etc.). Ontology and mapping files are **not validated at server startup** — problems surface only when you call `import_ontology`, `map_db_schema_to_ontology`, or when the graph is first accessed.

<Warning>
  **Always use absolute paths** for `SEMANTICA_KG_PATH`, `SEMANTICA_MAPPING_CONFIG`, and tool arguments like `file_path` / `mapping_config_path`. MCP clients spawn the server with an unpredictable working directory, so relative paths such as `config/airline_r2rml_db_mapping.yaml` often resolve to the wrong location or not at all.
</Warning>

#### Quick diagnostic

Call `get_graph_summary` first. It reports whether the configured graph file exists and whether ontology classes are present:

```json
{
  "node_count": 0,
  "ontology_class_count": 0,
  "kg_path": "/home/cdsw/semantica/data/airline_graph.json",
  "kg_path_exists": false,
  "graph_ready": false
}
```

| Field | What it tells you |
| :---- | :---------------- |
| `kg_path_exists: false` | `SEMANTICA_KG_PATH` points to a missing file — server starts with an empty in-memory graph |
| `ontology_class_count: 0` | No ontology loaded yet; `map_db_schema_to_ontology` will fail until you import one or fix `SEMANTICA_KG_PATH` |
| `graph_ready: false` | Graph has no nodes — either the KG file did not load or you have not imported data yet |

Set `SEMANTICA_LOG_LEVEL=INFO` (or `DEBUG`) and restart the client to see load warnings on stderr.

#### `SEMANTICA_KG_PATH` — persisted graph (includes pre-imported ontology)

Loaded once when the graph is first accessed. Behavior:

| Condition | Server behavior | What you see |
| :-------- | :-------------- | :----------- |
| Env var not set | Fresh in-memory graph | `kg_path: null`, `kg_path_exists: false` |
| Path set but file missing | Skips load silently | `kg_path_exists: false`, empty graph, no tool error |
| File exists but corrupt / unreadable | Warning on stderr, empty graph | `Could not load graph from …` in logs; graph appears empty |
| File exists and valid | Graph restored | `ontology_class_count > 0` if the file contains imported ontology |

**Fix:** Use an absolute path. Confirm the file exists on the machine where the MCP server runs (not just your laptop, if using Agent Studio or a remote workbench). Rebuild with `scripts/build_airline_graph.py` if needed.

```json
{
  "env": {
    "SEMANTICA_KG_PATH": "/home/cdsw/semantica/data/airline_graph.json",
    "SEMANTICA_LOG_LEVEL": "INFO"
  }
}
```

#### `SEMANTICA_MCP_TOOLSET` — limit exposed tools (optional)

Set a toolset preset so `tools/list` only advertises the tools you need. Useful when you prefer
env-based filtering instead of curating the tool checklist per agent (e.g. in Agent Studio):

| Preset | Tools exposed | Use when |
| :----- | :------------ | :------- |
| `preloaded_graph` | `get_graph_summary`, `get_business_rules`, `run_reasoning`, `record_decision` | Graph loaded via `SEMANTICA_KG_PATH`; no NER/build tools |
| `full` / unset | All tools | Local dev, full extraction pipeline |

Override with a comma-separated list: `SEMANTICA_MCP_TOOLS=get_graph_summary,get_business_rules`.

`SEMANTICA_MCP_DISABLE_ML=true` makes `extract_entities` / `extract_relations` fail fast (no spaCy load) if an old client still calls them.

#### `import_ontology` — loading OWL/TTL/RDF at runtime

Unlike `SEMANTICA_KG_PATH`, this tool fails explicitly and returns an `error` field:

| Condition | Tool response |
| :-------- | :------------ |
| Neither `file_path` nor `url` provided | `{"error": "Either file_path or url is required"}` |
| Local file does not exist | `{"error": "Ontology file not found: /absolute/path/to/ontology.ttl"}` |
| URL unreachable or invalid scheme | `{"error": "<download or network error>"}` |
| File unreadable or not valid RDF/OWL | `{"error": "<parse error from OntologyIngestor>"}` |
| `namespace_filter` too narrow | `{"status": "imported", …}` but `stats.skipped` is high and `class_nodes` may be `0` |

On success:

```json
{
  "status": "imported",
  "ontology_uri": "https://w3id.org/demo/airline#",
  "stats": { "class_nodes": 12, "property_nodes": 48, "skipped": 0 }
}
```

**Fix:** Verify the path with `ls` on the host running `semantica-mcp`. For remote ontologies, test the URL in a browser or with `curl` first. Remove or widen `namespace_filter` if classes are skipped.

#### `SEMANTICA_MAPPING_CONFIG` — ontology↔database mapping YAML

The mapping file is read **only when** `map_db_schema_to_ontology` is called. It is **not** loaded at server startup.

Resolution order:

1. `mapping_config_path` tool argument (if the file exists)
2. `SEMANTICA_MAPPING_CONFIG` environment variable (if the file exists)
3. If neither resolves to an existing file → **heuristic name-matching only** (no error)

<Warning>
  A missing or wrong mapping path does **not** return an error. The tool succeeds with `"used_mapping_config": false` and falls back to fuzzy table/column name matching. Explicit YAML rules are silently ignored — this is the most common misconfiguration.
</Warning>

| Condition | Tool response |
| :-------- | :------------ |
| Path missing / wrong / relative | `"used_mapping_config": false`, `"mapping_config_path": null` — heuristic suggestions only |
| File exists, valid YAML | `"used_mapping_config": true`, `"mapping_config_path": "/absolute/path/…"` |
| File exists but invalid YAML | `{"error": "<yaml parse error>"}` |
| File exists but `ontology_namespace` empty | Tables/columns stay `"status": "unmapped"` even with `tables:` entries |
| Ontology not in graph | `{"error": "No OntologyClass nodes in graph. Call import_ontology first or load a graph via SEMANTICA_KG_PATH."}` |

Successful mapping with explicit config:

```json
{
  "status": "ok",
  "used_mapping_config": true,
  "mapping_config_path": "/home/cdsw/semantica/config/airline_r2rml_db_mapping.yaml",
  "suggestions": {
    "summary": { "tables": 4, "tables_mapped": 4, "columns_mapped": 18 }
  },
  "applied": { "tables": 4, "columns": 18, "foreign_keys": 3 }
}
```

Silent fallback (mapping file not found):

```json
{
  "status": "ok",
  "used_mapping_config": false,
  "mapping_config_path": null,
  "suggestions": {
    "summary": { "tables": 4, "tables_mapped": 1 }
  }
}
```

**Fix checklist:**

1. Set `SEMANTICA_MAPPING_CONFIG` to the **absolute** path of your YAML (e.g. `/home/cdsw/semantica/config/airline_r2rml_db_mapping.yaml`).
2. Confirm `ontology_namespace` in the YAML matches the imported ontology URI prefix.
3. Table/column keys in YAML are normalized (lowercase, no underscores; umlauts → `ae`/`oe`/`ue`) — `arr_delay` and `arrdelay` both map to token `arrdelay`.
4. Call `import_ontology` (or load a pre-built graph via `SEMANTICA_KG_PATH`) **before** `map_db_schema_to_ontology`.
5. After mapping, check `"used_mapping_config": true` in the response — if `false`, the YAML was not found.

```json
{
  "env": {
    "SEMANTICA_KG_PATH": "/home/cdsw/semantica/data/airline_graph.json",
    "SEMANTICA_MAPPING_CONFIG": "/home/cdsw/semantica/config/airline_r2rml_db_mapping.yaml"
  }
}
```

#### Agent Studio / CDSW path mismatch

On Cloudera workbenches the repo is typically at `/home/cdsw/semantica`. Paths copied from a local laptop (e.g. `/Users/you/semantica/...`) will not exist on the workbench. Use the path cheat sheet in `deploy/cloudera-agent-studio/README.md` or generate config with:

```bash
python scripts/generate-agent-studio-mcp-config.py \
  --semantica-root /home/cdsw/semantica \
  --iceberg-root /home/cdsw/iceberg-mcp-server-hive
```

#### End-to-end recovery workflow

When ontology or mapping setup is broken, run this sequence:

```text
1. get_graph_summary()
   → check kg_path_exists and ontology_class_count

2. If ontology_class_count == 0:
     import_ontology(file_path="/absolute/path/to/ontology.ttl")
   → must return status "imported", not "error"

3. map_db_schema_to_ontology(
     schema_info=<from iceberg-mcp get_database_schema_info>,
     mapping_config_path="/absolute/path/to/mapping.yaml",
     apply_mappings=true
   )
   → confirm used_mapping_config == true

4. get_graph_summary()
   → ontology_class_count > 0, database_table_count > 0
```

## Related Guides

- [Reasoning & Rules](reasoning) — the engine behind the `run_reasoning` tool
- [Decision Intelligence](decision-intelligence) — how decisions are stored as causal graph nodes
- [Context Graphs](context-graphs) — the graph that `add_entity` and `add_relationship` write to
- [Export & Serialization](export) — all export formats available via `export_graph`
- [Ontology Management](ontology) — generate OWL ontologies from the graph built via MCP
