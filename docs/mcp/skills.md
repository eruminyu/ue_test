# Unreal MCP agent skills digest

Source: `ToolsetRegistry.AgentSkillToolset` / `ListSkills` + `GetSkills` on the running editor (UE 5.8.2, 2026-09-29).
Call shape: `{"toolset_name":"ToolsetRegistry.AgentSkillToolset","tool_name":"GetSkills","arguments":{"skillPaths":["<path>"]}}`.

## Skills available in this project (ListSkills)

| Skill path | Topic | Read? |
|---|---|---|
| `/EditorToolset/Python/editor_toolset/skills/blueprint_basics_PY.BlueprintBasicsSkill` | Creating/editing Blueprints | yes (core) |
| `/EditorToolset/Python/editor_toolset/skills/material_basics_PY.MaterialBasicsSkill` | Materials / MIs | yes |
| `/EditorToolset/Python/editor_toolset/skills/default_outdoor_lighting_PY.DefaultOutdoorLightingSkill` | Sun/sky/fog/exposure for a level | yes |
| `/EditorToolset/Python/editor_toolset/skills/unreal_skill_best_practices_PY.UnrealSkillBestPracticesSkill` | Writing skills | no |
| `/PCGToolset/Skills/Skill_InstantLevelOperations.Skill_InstantLevelOperations_C` | Quick PCG batch placement in level | yes |
| `/NiagaraToolsets/Python/skills/blueprint_interop_PY.NiagaraBlueprintInteropSkill` | Spawning Niagara from BP / cues | yes |
| `/NiagaraToolsets/Python/skills/level_placement_PY.NiagaraLevelPlacementSkill` | Placing VFX in level | yes |
| `/NiagaraToolsets/Python/skills/{fundamentals,renderers,optimization,custom_hlsl,cleanup}_PY.*` | Niagara authoring | no |
| `/PCGToolset/Skills/Skill_PCG*` (GraphGeneration, AssetZoo, BiomeCore, BiomeCoreRefinement, InstancingOnMeshActor, MeshPartition, ShapeGrammarDefinition) | PCG | no |
| `/Script/DataflowAgent.DataflowGraphEditingSkill` | Dataflow graphs | no |

**There is no skill for UMG, GAS (abilities/effects/attributes/cues), animation montages, or Enhanced Input.** For those, rely on the
toolset docstrings (UMGToolSet description has the mandatory list_properties workflow) and `docs/mcp/toolsets.md`.

---

## BlueprintBasicsSkill (core rules)

Reading graphs
- Read a graph as text with the DSL (`read_graph_dsl`) before modifying it.
- For large graphs, navigate instead of dumping: `find_nodes(entry_points_only=true)` -> `get_connected_subgraph(node)` isolates one event chain.

Writing graphs
- Populate event and function graphs with the DSL (`write_graph_dsl`).
- **Never guess node type IDs or pin names.** Look up with `find_node_types` and confirm pins with `get_node_type_pins` before writing DSL or `connect_pins`.
- Functions for logic that returns values / is reused; Event Graph for event-driven and latent/async logic.
- Compile only once all graph edits for a logical unit are complete.

Batch operations
- Work spanning multiple assets (many BPs, bulk variables, reparenting) -> programmatic tool calling (ProgrammaticToolset `execute_tool_script`) instead of many single calls.
  (Project rule still applies: record such steps as "Python".)

Gotchas
- Pure node outputs are not cached: every wire from a pure output re-runs it. Bind/store results used more than once (DSL: `bind`).
- Casting to a Blueprint creates a hard load dependency; prefer interfaces for loose coupling. (Note: no MCP tool adds an interface to a BP — see toolsets.md capability table.)
- Structural changes (components, variables, signatures) don't reach the CDO or new instances until the BP is compiled. Compile before `get_default_object` / ObjectTools CDO edits.
- Runtime physics needs Movable mobility; components often default to Static — set Mobility to Movable before simulate/impulse.

## MaterialBasicsSkill

- Order: (1) search for an existing Material/MI that fits, (2) create an MI from a suitable parent, (3) new Material only if nothing fits.
- New Material: reuse existing MaterialFunctions; expose per-instance parameters, grouped.
- Gotchas: neutral normal = (0,0,1); each static switch doubles shader permutations — keep few.
- For greybox color coding: `MaterialInstanceTools.create` from an engine/basic parent in `/Game/_Scratch`, set a Vector param.

## DefaultOutdoorLightingSkill (only if we build a new level from scratch)

- Outdoor lighting = 6 actors: Directional Light (sun, the driver), Sky Atmosphere, Exponential Height Fog, Sky Light, Volumetric Clouds, Post Process Volume.
  Sun intensity 0 -> black sky and invisible clouds.
- Sun rotation: pitch 0 = horizon, -90 = overhead; yaw 0 = north.
- **Never read/set properties on the lighting actor itself — use `ActorTools.get_components` then ObjectTools on the component.**
- Realistic lux (80k–120k direct sun). Exposure bias: auto-exposure active (min/max overridden) -> small ±2 EV; not active -> large negative (−10 to −14 EV for full sun). Read the Post Process min/max brightness first; enable the bias override when setting it.
- Don't edit engine cloud material; duplicate into project first.
- Screenshot loop: baseline capture -> change -> capture -> at most 3 refinement cycles, then report.
- Practical shortcut for the demo: duplicate an existing lit template map into `/Game/_Scratch` instead of building lighting (template maps already have these actors).

## Skill_InstantLevelOperations (PCG)

- Pre-built instant PCG graphs in `/PCGPrimitives/Instants/` run via `RunPCGInstantGraph(InstantGraphObject, {params})` in the **PCGSpatialToolset**
  (`PCGToolset.PCGSpatialToolset`, not surveyed here). Load the graph with `GetGraphStructure` first to map parameters.
- For quick batch placement (actor grids/lines, transforms, spline shapes) without authoring a graph; results appear async; chain only after the previous op succeeded.
- Must ask the user before any delete operation. Ask for missing parameters only when undefined.
- For our needs (a few enemies, floor, walls) SceneTools `add_to_scene_from_class/asset` is simpler.

## NiagaraBlueprintInteropSkill (hit FX)

- Choose one spawn mechanism: component on the actor (effect is part of the actor), **Spawn at Location** (one-shot, no owner; capture return value for params),
  Spawn Attached (follows a target you don't own), **Gameplay Cue Notify** (whenever a gameplay tag association exists — preferred for GAS hit/death FX),
  anim notify (timing from animation), Niagara Data Channel (high-frequency events).
- Set User Parameters from BP with typed Set Niagara Variable nodes; pass bare name (no `User.` prefix); no enum setter (set int); wrong type = silent no-op;
  world positions use Position type, directions Vector3.
- Pooling is chosen on the spawn node: repeating one-shots should use auto-release pooling; set Auto Destroy true on fire-and-forget spawns.

## NiagaraLevelPlacementSkill

- When asked to place VFX: search the project (and Niagara / NiagaraToolsets plugin templates) for candidates, present them with location + description,
  **stop and let the user pick**. Don't place the first match; don't author a new system unless explicitly asked.

---

## Cross-cutting rules distilled from toolset docstrings (no skill covers them)

- UMG: for every widget/slot returned, `ObjectTools.list_properties` -> `get_properties` -> `set_properties`; names can't be guessed; skipping list = silent failure.
  Compile with `CompileWidgetBlueprint`; save with AssetTools `save_assets([paths])`.
- Tags / cue tags / skills: `AddTag`, `RemoveTag`, `RenameTag`, `AddCueTag`, `RemoveCueTag`, `CreateCueNotifyAsset`, `CreateSkill`, `UpdateSkill` docstrings say
  "ONLY after explicit direction or permission from the user".
- `AddTag`/`AddCueTag` schema default for `comment` is the raw C++ doc comment — always pass `comment`.
- LogsToolset `category` defaults to `"LogsToolset"` — always pass `category` (`""` for all).
- `save_assets([])` saves ALL dirty assets (would include template assets dirtied by read tools) — always pass explicit paths.
- ProgrammaticToolset is a sandbox (json/math/re/datetime/time/copy only); it is not editor Python.
