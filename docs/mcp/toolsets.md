# Unreal MCP toolset reference (SoulCombat, UE 5.8.2)

Source: `list_toolsets` + `describe_toolset` on the running editor (2026-09-29). Read-only survey; nothing was called except
describe/list, `get_graph_dsl_docs`, `get_execution_environment`, skill reads, and two `find_assets` + `get_current_level` lookups
(no assets created or modified). Statuses in the capability table at the end are from documentation only.

## How to call

- Load MCP tools once: `ToolSearch` query `select:mcp__unreal-mcp__list_toolsets,mcp__unreal-mcp__describe_toolset,mcp__unreal-mcp__call_tool`.
- Call: `mcp__unreal-mcp__call_tool {toolset_name: "<full toolset name>", tool_name: "<short tool name>", arguments: {...}}`.
  `tool_name` is the short name (e.g. `create_node`), not the dotted full name that `describe_toolset` prints.
- Object/class arguments are always `{"refPath": "<soft path>"}`. Examples:
  - Blueprint asset: `{"refPath": "/Game/_Scratch/BP_Foo.BP_Foo"}`
  - Native class: `{"refPath": "/Script/Engine.Actor"}`, `{"refPath": "/Script/SoulCombat.SCAttributeSet"}`
  - BP generated class: `{"refPath": "/Game/_Scratch/BP_Foo.BP_Foo_C"}`
  - Struct: `{"refPath": "/Script/GameplayTags.GameplayTag"}`, `{"refPath": "/Script/Engine.HitResult"}`
  - Graphs/nodes: use the `refPath` strings returned by other tools (e.g. `get_graph`, `create_node`) verbatim.
- `PinID` = `{"node": {"refPath": ...}, "direction": "EGPD_Input"|"EGPD_Output", "index_id": <int>}`. Get PinIDs from
  `get_node_infos` / `get_node_type_pins` / `get_connected_subgraph` (field `pin_id`).
- `IntPoint` = `{"x": int, "y": int}`.
- Returns come back as `{"returnValue": ...}`. Many tools report failure only inside the payload; always read the result.
- Notation below: `arg?` = optional, `=x` = default, `ref<Class>` = `{"refPath": ...}` of that class, `[T]` = array,
  `-> T` = return type.

Toolset full names (for `toolset_name`):

| Short | Full toolset_name |
|---|---|
| BlueprintTools | `editor_toolset.toolsets.blueprint.BlueprintTools` |
| ObjectTools | `editor_toolset.toolsets.object.ObjectTools` |
| AssetTools | `editor_toolset.toolsets.asset.AssetTools` |
| DataAssetTools | `editor_toolset.toolsets.data_asset.DataAssetTools` |
| DataTableTools | `editor_toolset.toolsets.data_table.DataTableTools` |
| UMGToolSet | `UMGToolSet.UMGToolSet` |
| SceneTools | `editor_toolset.toolsets.scene.SceneTools` |
| ActorTools | `editor_toolset.toolsets.actor.ActorTools` |
| PrimitiveTools | `editor_toolset.toolsets.primitive.PrimitiveTools` |
| MaterialInstanceTools | `editor_toolset.toolsets.material_instance.MaterialInstanceTools` |
| StaticMeshTools | `editor_toolset.toolsets.static_mesh.StaticMeshTools` |
| GameplayTagsToolset | `GameplayTagsToolset.GameplayTagsToolset` |
| GameplayCueToolset | `GASToolsets.GameplayCueToolset` |
| AttributeSetToolset | `GASToolsets.AttributeSetToolset` |
| AbilitySystemInspectorToolset | `GASToolsets.AbilitySystemInspectorToolset` |
| EditorAppToolset | `EditorToolset.EditorAppToolset` |
| LogsToolset | `EditorToolset.LogsToolset` |
| ConfigSettingsToolset | `ConfigSettingsToolset.ConfigSettingsToolset` |
| ProgrammaticToolset | `editor_toolset.toolsets.programmatic.ProgrammaticToolset` |
| SlateInspectorToolset | `SlateInspectorToolset.SlateInspectorToolset` |
| AgentSkillToolset | `ToolsetRegistry.AgentSkillToolset` |
| NiagaraToolset_Component | `NiagaraToolsets.NiagaraToolset_Component` |
| SkeletalMeshTools (extra) | `editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools` |

Other toolsets present but not described here: AutomationTestToolset.AutomationTestToolset, DataRegistryToolset.DataRegistryTools,
DataflowAgent.DataflowAgentToolset, GameFeaturesToolset.GameFeaturesToolset, NiagaraToolsets.{NiagaraToolset_Info, NiagaraToolset_Blueprint,
NiagaraToolset_System, NiagaraToolset_Assets}, PhysicsToolsets.PhysicsAssetToolset, SemanticSearchToolset.SemanticSearchToolset,
PluginToolset.PluginToolset, WorldConditionsToolset.WorldConditionTools, PCGToolset.{PCGToolset, PCGSpatialToolset},
state_tree_toolset.toolsets.state_tree.StateTreeTools, editor_toolset.toolsets.{curve_table.CurveTableTools, material.MaterialTools,
string_table.StringTableTools, texture.TextureTools}, aimodule_toolset.toolsets.behavior_tree.BehaviorTreeTools,
conversation_toolset.toolsets.conversation.ConversationTools, animation_toolset.toolsets.{controlrig.ControlRigTools, sequencer.SequencerTools,
keyframing.SequencerKeyframingTools, controlrig_sequencer.SequencerControlRigTools, outliner.SequencerOutlinerTools,
conditions.SequencerConditionTools, custom_bindings.SequencerCustomBindingTools, import_export.SequencerImportExportTools}.

---

## BlueprintTools (`editor_toolset.toolsets.blueprint.BlueprintTools`) — 53 tools

Types used: `PinID{node: ref<EdGraphNode>, direction: EGPD_Input|EGPD_Output, index_id:int}`, `IntPoint{x,y}`,
`NodeInfo{node: ref, type_id: str, position: IntPoint, input_pins: [PinInfo], output_pins: [PinInfo]}`,
`PinInfo{name: str, type_id: str, value: str, pin_id: PinID, connected_pins: [PinID]}`,
`BlueprintFunctionInfo{name, description, bIsImplemented: bool}`.
`container_type` enum everywhere: `ARRAY | SET | MAP` (MAP key is always **string**; no way to choose key type).

### Asset / class level
- `create(folder_path: str, asset_name: str, asset_type: ref<Class>) -> ref<Blueprint>` — create a new BP asset.
  `asset_type` = parent class (e.g. `/Script/Engine.Actor`, `/Script/Engine.Character`, `/Script/GameplayAbilities.GameplayAbility`).
  Example: `{"folder_path":"/Game/_Scratch","asset_name":"BP_Test","asset_type":{"refPath":"/Script/Engine.Actor"}}`.
- `compile_blueprint(blueprint: ref<Blueprint>, warnings_as_errors?: bool =false)` — compile; call after all graph edits.
- `set_parent(blueprint, parent_class: ref<Class>)` — reparent (recompile after).
- `get_parent(blueprint) -> ref<Class>`.
- `get_default_object(blueprint) -> ref<Object>` — CDO (compile first). ObjectTools get/set/list already resolve the CDO when
  given a Blueprint, so use this mainly before ActorTools calls.

### Graphs, functions, events
- `list_graphs(blueprint) -> [ref<EdGraph>]`.
- `get_graph(blueprint, graph_name: str) -> ref<EdGraph>` — e.g. `"EventGraph"`, a function name.
- `add_function_graph(blueprint, graph_name: str) -> ref<EdGraph>` — new function; if name matches an inherited overridable
  function it creates an override. Idempotent.
- `remove_function_graph(blueprint, graph_name: str)` — removes function or dispatcher. **Closes the BP editor window if open.**
- `add_event(blueprint, event_name: str, position?: IntPoint ={0,0}) -> ref<EdGraphNode>` — override inherited event (e.g.
  `ReceiveBeginPlay`, `ReceiveAnyDamage`, `K2_ActivateAbility`) or create a custom event with that name. Idempotent.
- `list_events(blueprint) -> [BlueprintFunctionInfo]` — local custom events + inheritable events (parents and implemented interfaces).
- `list_functions(blueprint) -> [BlueprintFunctionInfo]` — local + inheritable functions (parents and interfaces).
- `add_function_param(graph, param_name: str, param_type: str, input_param: bool, container_type?) -> PinID` —
  `param_type` one of `bool,int,float,byte,string,name,text,Vector,Rotator,Transform,Vector2D,LinearColor`.
  Output params not supported on event dispatchers.
- `add_object_function_param(graph, param_name, object_class: ref<Class>, input_param: bool, container_type?) -> PinID`.
- `add_struct_function_param(graph, param_name, struct_type: ref<ScriptStruct>, input_param: bool, container_type?) -> PinID`.
- `remove_function_param(graph, param_name: str, input_param: bool)`.

### Event dispatchers / delegates
- `add_event_dispatcher(blueprint, name: str) -> ref<EdGraph>` — add params with the `add_*_function_param` tools on the returned graph.
- `list_event_dispatchers(blueprint) -> [ref<EdGraph>]`.
- `list_compatible_event_functions(node: ref<K2Node_CreateDelegate>) -> [str]` — functions bindable to a Create Event node.
- `set_create_event_function(node: ref<K2Node_CreateDelegate>, function_name: str)` — bind function to Create Event node.
- `get_create_event_function(node) -> str`.
- `add_component_bound_event(component: ref<ActorComponent>, event_name: str, graph: ref<EdGraph>) -> ref<EdGraphNode>` —
  e.g. `OnComponentBeginOverlap` on a component of a BP actor (component ref = the component template inside the BP).
- `list_component_events(component) -> [str]`.

### Variables
- `add_variable(blueprint, name: str, type_name: str, graph?: ref<EdGraph>, container_type?)` — `type_name` one of
  `bool,int,float,byte,string,name,text,Vector,Rotator,Transform,Vector2D,LinearColor`. `graph` set = local variable.
- `add_object_variable(blueprint, name, object_class: ref<Class>, graph?, container_type?)` — object reference variable
  (NOT a class reference / TSubclassOf; no class-ref variant is documented).
- `add_struct_variable(blueprint, name, struct_type: ref<ScriptStruct>, graph?, container_type?)` — any UStruct
  (GameplayTag, GameplayTagContainer, HitResult, user structs...).
- `remove_variable(blueprint, name: str, graph?)`.
- `list_variables(blueprint, graph?) -> [str]`.
- `set_variable_category(blueprint, variable_name, category: str)` / `get_variable_category(blueprint, variable_name) -> str`.
- `set_variable_replication(blueprint, variable_name, replication: None|Replicated|RepNotify)` (RepNotify auto-creates OnRep_) /
  `get_variable_replication(...)`.
- `set_variable_instance_editable(blueprint, variable_name, instance_editable: bool)`.
- Variable default values: set on the CDO via ObjectTools `set_properties` with the Blueprint ref (compile first).
- No tool to change an existing variable's type (and doing so in UI can open a modal) — remove and re-add instead.

### Nodes and pins (low-level graph editing)
- `find_node_types(graph, type_id_filter: str, context_pins: [PinID]) -> [str]` — search creatable node type_ids
  (case-insensitive substring). Trailing `|` lists a category (e.g. `"Utilities|FlowControl|"`). Pass `context_pins: []`
  when not filtering. Keep filter specific (thousands of types). **May dirty the BP it inspects — only call on _Scratch BPs.**
- `find_node_categories(graph, category_filter: str, context_pins: [PinID]) -> [str]`.
- `get_node_type_pins(graph, type_id: str) -> NodeInfo` — pins of a node type before creating it.
- `create_node(graph, type_id: str, pos: IntPoint, declaring_class?: ref<Class>) -> ref<EdGraphNode>` — type_id examples:
  `Development|PrintString`, `Utilities|Operators|Add`, macro `Utilities|FlowControl|ForLoop`, dispatcher handler
  `Default|EventDispatcherOnDamaged`, event `AddEvent|EventBeginPlay`, custom event `AddEvent|Custom|MyEventName`.
  `declaring_class` only to disambiguate identical type_ids.
- `delete_node(node)`.
- `set_node_position(node, pos: IntPoint)` — move a node.
- `arrange_nodes(nodes: [ref<EdGraphNode>])` — auto-layout left-to-right by exec/data flow; outside connections act as anchors.
  Call after building a graph.
- `get_node_infos(nodes: [ref]) -> [NodeInfo]` — type, pins (with PinIDs, values, connections), position.
- `find_nodes(graph, title: str, node_class?: ref<Class>, entry_points_only?: bool =false) -> [ref<EdGraphNode>]` — title
  substring (empty = any); `entry_points_only` = events/function entries.
- `get_connected_subgraph(node) -> [NodeInfo]` — all nodes reachable via any connection (read one event chain).
- `connect_pins(output_pin: PinID, input_pin: PinID)` / `break_pins(output_pin, input_pin)`.
- `get_pin_value(pin: PinID) -> str` / `set_pin_value(pin: PinID, value: str)` — input pin defaults. Formats: `"42"`, `"3.14"`,
  `"true"`, `"Hello"`, object `"/Game/Path/Asset.Asset"`.
- `add_node_pin(node) -> PinID` / `remove_node_pin(node, pin: PinID)` — Switch cases, Sequence outputs, commutative ops, Make Array.
- `retarget_node_class(node, old_class: ref<Class>, new_class: ref<Class>)` — fix class refs after duplicating a BP (cast,
  call, event, delegate nodes). Compile after.

### Graph DSL (high-level, preferred for bulk logic)
- `get_graph_dsl_docs() -> str` — full syntax (saved to `docs/mcp/graph-dsl.md`).
- `read_graph_dsl(graph) -> str` — S-expression script of the graph.
- `write_graph_dsl(graph, code: str)` — populate graph from DSL **and compile the BP**.

---

## ObjectTools (`editor_toolset.toolsets.object.ObjectTools`) — 6 tools

Works on any UObject: assets, BP CDOs (pass the Blueprint ref; CDO resolved automatically), actors, components, widgets, UMG slots,
data assets, classes.

- `list_properties(instance: ref<Object>) -> str` — property names (and types) on the object. **Call before get/set**; names
  cannot be guessed (UMG slots/widgets especially).
- `get_properties(instance, properties: [str]) -> str` — JSON string of the requested values.
- `set_properties(instance, values: str) -> bool` — `values` is a **JSON-formatted string** (not an object), e.g.
  `"{\"MaxWalkSpeed\": 600.0}"`. For instanced sub-object properties pass a class path as the value. Returns False on failure
  (no exception) — check it and re-read with get_properties.
- `reset_properties(instance, properties: [str]) -> bool` — revert to defaults (drop overrides).
- `get_class(instance) -> ref<Class>`.
- `search_subclasses(base_class: ref<Class>, class_name: str) -> [ref<Class>]` — find subclasses; `class_name` is a
  case-insensitive substring filter on the class path (required; pass `""` for all).

Typical: set a TSubclassOf / class property on a CDO or data asset with `set_properties` using a class path string, e.g.
`"{\"Ability\": \"/Game/_Scratch/GA_Test.GA_Test_C\"}"` (format untested; confirm with get_properties).

---

## AssetTools (`editor_toolset.toolsets.asset.AssetTools`) — 21 tools

Paths are plain strings (content paths like `/Game/_Scratch/BP_Foo`), not refPath objects (except `asset_type`).
**No generic "create asset of class X" tool here** (asset creation is per-toolset: BlueprintTools.create, DataAssetTools, DataTableTools, UMG...).

- `find_assets(folder_path: str, name: str, asset_type?: ref<Class> =null, recursive?: bool =true, tags?: map<str,str> =null) -> [str]` —
  `folder_path ""` = whole project incl. plugins; `name` substring (case-insensitive; `""` = any); `tags` exact AR tag matches.
- `exists(path: str) -> bool` — asset or folder.
- `list_folders(root_path: str, recursive?: bool =true) -> [str]`. (Arg is `root_path`, the docstring says `root`.)
- `create_folder(path: str) -> bool` — True if created or already exists.
- `load_asset(asset_path: str) -> ref<Object>` — get a refPath for an asset.
- `get_asset_class(asset_path: str) -> str` — e.g. `StaticMesh`, `HeroCharacter_C`.
- `get_asset_tags(asset_path) -> map<str,str>` — asset registry tags.
- `get_metadata_tags(asset_path) -> map<str,str>` / `update_metadata_tags(asset_path, set_tags?: map<str,str>, remove_tags?: [str])`.
- `get_dependencies(asset_path) -> [str]` / `get_referencers(asset_path) -> [str]`.
- `duplicate(path: str, new_path: str) -> bool` — copy asset or folder (use to copy template assets into `/Game/_Scratch`).
- `move(path, new_path) -> bool` — move/rename asset or folder.
- `delete(path) -> bool` — delete asset or folder.
- `save_assets(asset_paths: [str]) -> bool` — save listed assets. **Empty list = save ALL dirty assets (includes dirtied template assets — never pass `[]`).**
- `is_dirty(asset_path) -> bool` — unsaved changes?
- `is_checked_out(asset_path) -> bool`, `can_edit_asset(asset_path) -> bool` — source control.
- `read_file(file_path: str) -> str` / `write_file(file_path: str, content: str)` — plain-text files only under `/Game/`, an enabled
  plugin's `Content/`, or project `Saved/`. `write_file` overwrites.
- `get_plugin_content_paths(include_engine?: bool =false) -> [str]` — e.g. `['/PluginName/']`.

---

## DataAssetTools (`editor_toolset.toolsets.data_asset.DataAssetTools`) — 1 tool

- `create(folder_path: str, asset_name: str, asset_type: ref<Class>) -> ref<DataAsset>` — create a DataAsset instance of a
  (Primary)DataAsset subclass, e.g. `{"folder_path":"/Game/_Scratch","asset_name":"DA_Test","asset_type":{"refPath":"/Script/SoulCombat.SCAbilitySet"}}`.
  Fill fields afterwards with ObjectTools `list_properties` / `set_properties` on the returned ref.

---

## DataTableTools (`editor_toolset.toolsets.data_table.DataTableTools`) — 10 tools

- `create(folder_path: str, asset_name: str, schema: ref<ScriptStruct>) -> ref<DataTable>` — schema must derive from
  TableRowBase (e.g. `/Script/GameplayAbilities.AttributeMetaData` for attribute init tables; verify with search_row_structs).
- `import_file(folder_path, asset_name, source_file: str (absolute disk path), schema: ref<ScriptStruct>) -> [ref<Object>]` —
  CSV/JSON columns must match schema property names.
- `search_row_structs(struct_name?: str ="*") -> [ref<ScriptStruct>]` — wildcard filter.
- `get_schema(data_table) -> str` — JSON column-name -> type info.
- `list_rows(data_table) -> [str]`.
- `add_rows(data_table, row_names: [str])` — new rows with default values.
- `set_rows(data_table, values: str)` — **JSON string** `{"RowName": {"camelCaseProp": value, ...}}`; only listed props change.
  Note: docstring says camelCase property names; check `get_schema`/`get_rows` output for the exact casing.
- `get_rows(data_table, row_names: [str]) -> str` — JSON.
- `rename_rows(data_table, renames: map<str,str>)` — old -> new.
- `remove_rows(data_table, row_names: [str])`.

---

## UMGToolSet (`UMGToolSet.UMGToolSet`) — 23 tools

Arg names are **camelCase** here (unlike the snake_case editor_toolset tools). Widget/slot refs returned by these tools are passed
straight to ObjectTools. Required workflow per widget and slot: `ObjectTools.list_properties` -> `get_properties` -> `set_properties`
(names vary per class and cannot be guessed; skipping list causes silent failures).
`UMGWidgetInfo = {widget, parent, slot, namedSlotHost, widgetClassPath, widgetName, bIsVariable, bInherited, uIComponents[]}`.
WBP ref = `{"refPath": "/Game/_Scratch/WBP_X.WBP_X"}` (no `_C`).

Create / compile
- `CreateWidgetBlueprint(folderPath: str, assetName: str, parentClass: ref<Class of UserWidget>) -> ref<WidgetBlueprint>` —
  parentClass usually `/Script/UMG.UserWidget`. Returns null on failure.
- `CompileWidgetBlueprint(widgetBlueprint) -> bool` — false + error details on failure (missing BindWidget, type mismatch, graph errors).
  Save separately with AssetTools `save_assets`.

Read
- `GetWidgets(widgetBlueprint) -> {info:{parentClass, rootWidgetClass, widgetCount, inheritedWidgetCount, namedSlotCount}, widgets:[UMGWidgetInfo]}` — depth-first, slot order.
- `GetWidgetDescription(widgetBlueprint, startWidget?: ref<Widget> =null, maxDepth?: int =-1) -> {description: str, widgets: [UMGWidgetInfo]}` —
  full property dump, one line per widget `[N] Type Name Prop:Value ... slot:(...)`; N indexes `widgets`. (-1 no limit, 0 start only.)
- `GetWidgetTreeDepth(widgetBlueprint, startWidget?) -> int`.
- `GetNamedSlots(widgetBlueprint) -> [{slotName, hostWidget, contentWidget}]`.
- `ListWidgetBlueprints(folderPath: str) -> [ref]` — recursive.
- `ListWidgetClasses(filter: str) -> [{widgetClass, bIsPanel, category, description}]` — `""` = all.
- `GetWidgetClassInfo(widgetClass: ref<Class>) -> {widgetClass, bIsPanel, category, description}`.

Edit tree
- `AddWidget(widgetBlueprint, widgetClass: ref<Class>, widgetDisplayName: str, parentWidget?: ref<Widget> =null, childIndex?: int =-1) -> UMGWidgetInfo` —
  null parent + empty tree = becomes root (e.g. `/Script/UMG.CanvasPanel`). Classes: `/Script/UMG.ProgressBar`, `/Script/UMG.TextBlock`,
  `/Script/UMG.Button`, `/Script/UMG.Image`, `/Script/UMG.VerticalBox`, ...
- `RemoveWidget(widgetBlueprint, widget) -> bool` — removes children too.
- `MoveWidget(widgetBlueprint, widget, newParent: ref<PanelWidget>, childIndex?: int =-1) -> UMGWidgetInfo` (new slot).
- `WrapWidgets(widgetBlueprint, widgets: [ref<Widget>], wrapperClass: ref<Class of PanelWidget>) -> [UMGWidgetInfo]`.
- `RenameWidget(widgetBlueprint, widget, newDisplayName: str) -> UMGWidgetInfo` (empty on failure).
- `ToggleWidgetAsVariable(widgetBlueprint, widget, bIsVariable: bool)` — expose as BP variable (needed before binding events / graph access).
- `SetNamedSlotContent(widgetBlueprint, hostWidget: ref|null, slotName: str, widgetClass: ref<Class>, widgetName: str) -> UMGWidgetInfo`.
- `ReplaceWidgetWithTemplate(widgetBlueprint, widgetToReplace, templateClass: ref<Class>) -> {bSuccess, missingReferencesWarning, unmatched...[]}`.
- `ReplaceWidgetWithNamedSlot(widgetBlueprint, widgetToReplace, namedSlot: str) -> bool`.
- `ReplaceWidgetWithChild(widgetBlueprint, widgetToReplace) -> bool` — panel with exactly one child.
- `AddUIComponent(widgetBlueprint, widgetName: str, componentClass: ref<Class of UIComponent>) -> UMGWidgetInfo`;
  `RemoveUIComponent(widgetBlueprint, widgetName, componentClass) -> bool`;
  `MoveUIComponent(widgetBlueprint, widgetName, componentClassToMove, relativeToComponentClass, bMoveAfter: bool) -> bool`.

Events
- `BindToEventProperty(widgetBlueprint, eventName: str, propertyName: str, propertyClass: ref<Class>) -> bool` — adds a BP event
  handler node bound to a widget's multicast delegate, e.g. `{"eventName":"OnClicked","propertyName":"Btn_Start","propertyClass":{"refPath":"/Script/UMG.Button"}}`.
  Preconditions: `propertyName` must exist as a BP variable (ToggleWidgetAsVariable true); `propertyClass` declares the delegate.
  Other events: OnPressed/OnReleased/OnHovered/OnUnhovered (Button), OnCheckStateChanged (CheckBox), OnValueChanged (Slider).
  Graph logic for the handler: find the node via BlueprintTools `find_nodes` on the WBP EventGraph, then DSL/create_node.
- No UMG tool for property bindings (Bind dropdown / `Get<Prop>` functions) or widget animations — use graph logic instead (e.g. set percent in an update function).

---

## SceneTools (`editor_toolset.toolsets.scene.SceneTools`) — 19 tools

`ToolsetTransform xform = {location?: {x,y,z}, rotation?: {pitch,yaw,roll}, scale?: {x,y,z}}` — unset = identity on create,
"don't change" on modify. Pass `{}` for identity.
**No "create new level" tool.** Workaround candidates: AssetTools `duplicate` an existing map into `/Game/_Scratch` then `load_level`,
or ProgrammaticToolset/Python. Beware: `load_level` while the current level is dirty may open a save-changes modal.

Level
- `get_current_level() -> str` — path of loaded level.
- `load_level(level_path: str)` — e.g. `/Game/_Scratch/L_Test`. (Modal risk if current level dirty.)
- `create_level_instance(level_path: str, name: str, xform, parent?: ref<Actor>) -> ref<LevelInstance>`;
  `edit_level_instance(level_instance)`; `commit_level_instance(level_instance, discard?: bool =false)`.

Actors
- `add_to_scene_from_class(actor_type: ref<Class>, name: str, xform, parent?: ref<Actor> =null, snap_to_ground?: bool =false) -> ref<Actor>` —
  e.g. `{"actor_type":{"refPath":"/Game/_Scratch/BP_Enemy.BP_Enemy_C"},"name":"Enemy1","xform":{"location":{"x":500,"y":0,"z":100}}}`
  or native `/Script/Engine.PlayerStart`, `/Script/NavigationSystem.NavMeshBoundsVolume`, `/Script/Engine.DirectionalLight`.
- `add_to_scene_from_asset(asset_path: str, name: str, xform, parent?, snap_to_ground?: bool =false) -> ref<Actor>` — spawn from
  an asset (static mesh, BP) e.g. `/Engine/BasicShapes/Cube`.
- `remove_from_scene(actor) -> bool`.
- `find_actors(name: str, tag: str, collision_channels: [ObjectTypeQueryN], root?: ref<Actor>, actor_type?: ref<Class>, bounds?: {min,max,isValid}) -> [ref<Actor>]` —
  `name`, `tag`, `collision_channels` are REQUIRED: pass `""`, `""`, `[]` to not filter.
- `get_collision_channels() -> [ObjectTypeQuery1..64]`.
- `trace_world(start: {x,y,z}, end: {x,y,z}) -> number|None` — distance to first hit.
- `merge_actors(actors: [ref<StaticMeshActor>], output_path: str, name: str, destroy_source_actors?: bool =false) -> ref<StaticMeshActor>`.
- `save_actor(actor)` — save actor to disk (OFPA/World Partition external actor).
- `is_checked_out(actor) -> bool`, `can_edit(actor) -> bool`.

Outliner folders
- `set_actor_folder(actor, folder_path: str)` (`""` = root), `get_actors_in_folder(folder_path, recursive?: bool =false) -> [ref<Actor>]`,
  `get_folders() -> [str]`, `rename_folder(old_path, new_path) -> int`, `delete_folder(folder_path) -> int`.

---

## ActorTools (`editor_toolset.toolsets.actor.ActorTools`) — 17 tools

Works on level actor instances and (for components/transforms) on Blueprint actors: `add_component.owner` accepts a Blueprint asset ref.
For other calls that need an Actor inside a BP, pass `BlueprintTools.get_default_object(bp)` (compiled first).

Components
- `add_component(owner: ref<Object> (BP asset, actor instance, or SceneComponent), component_type: ref<Class>, name: str) -> ref<ActorComponent>` —
  e.g. `{"owner":{"refPath":"/Game/_Scratch/BP_Enemy.BP_Enemy"},"component_type":{"refPath":"/Script/GameplayAbilities.AbilitySystemComponent"},"name":"ASC"}`.
  Owner = a SceneComponent attaches under it (e.g. hitbox under mesh).
- `remove_component(component) -> bool`.
- `get_components(actor: ref<Actor>, component_type?: ref<Class>) -> [ref<ActorComponent>]`.
- `get_root_component(actor) -> ref<SceneComponent>|None`.
- `set_parent_component(component: ref<SceneComponent>, parent?: ref<SceneComponent> =null) -> bool` — on BPs, parenting the root
  to a component promotes that component to root (DefaultSceneRoot auto-removed). null = detach.
- `get_parent_component(component) -> ref|None`, `get_component_actor(component) -> ref<Actor>`.
- Component properties (collision, mesh, socket `AttachSocketName`?, sizes): ObjectTools list/get/set on the component ref.

Transform / misc
- `get_actor_transform(actor) -> ToolsetTransform` (world).
- `set_actor_transform(actor, xform: ToolsetTransform, worldspace?: bool =true) -> bool` — on BP actors only relative transform applies.
- `look_at(actor, target: {x,y,z})`.
- `get_actor_bounds(actor) -> {min, max, isValid}`.
- `set_label(actor, label: str) -> bool`, `get_label(actor) -> str`.
- `add_tag(actor, tag: str)`, `remove_tag(actor, tag)`, `has_tag(actor, tag) -> bool`, `get_tags(actor) -> [str]` (Actor Tags, not GameplayTags).

---

## PrimitiveTools (`editor_toolset.toolsets.primitive.PrimitiveTools`) — 4 tools

All add a StaticMeshComponent (engine basic shape) to an **actor** (`ref<Actor>`; for a BP pass its CDO or try the BP ref — untested)
and return `ref<StaticMeshComponent>`. `local_transform?: ToolsetTransform =null`.
- `add_cube(actor, name: str, dimensions?: {x,y,z} ={100,100,100}, local_transform?)`
- `add_sphere(actor, name, radius?: number =50, local_transform?)`
- `add_cylinder(actor, name, radius?: number =50, height?: number =100, local_transform?)`
- `add_cone(actor, name, radius?: number =50, height?: number =100, local_transform?)`
Use for greybox placeholders (enemy body, weapon, floor blocks). Material via MaterialInstanceTools/ObjectTools on the component.

---

## MaterialInstanceTools (`editor_toolset.toolsets.material_instance.MaterialInstanceTools`) — 13 tools

`instance` = `ref<MaterialInstanceConstant>`; `parent`/`material` = `ref<MaterialInterface>`.
- `create(folder_path: str, asset_name: str, parent: ref<MaterialInterface>) -> ref<MaterialInstanceConstant>` — e.g. parent
  `/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial` (has `Color` vector param — verify with list_parameters).
- `list_parameters(material) -> [{name, type: Scalar|Vector|Texture|StaticSwitch}]`.
- `set_scalar_parameter(instance, name: str, value: number)` / `get_scalar_parameter(instance, name) -> number`.
- `set_vector_parameter(instance, name, value: {r,g,b,a})` (>1 ok for emissive) / `get_vector_parameter(instance, name) -> {r,g,b,a}`.
- `set_texture_parameter(instance, name, value: ref<Texture>)` / `get_texture_parameter(instance, name) -> ref<Texture>|None`.
- `set_static_switch_parameter(instance, name, value: bool)` (shader recompile) / `get_static_switch_parameter(instance, name) -> bool`.
- `set_parameter_override(instance, name, override: bool)` — toggle override (disabling discards non-static values).
- `clear_parameters(instance)` — revert all to parent.
- `set_parent(instance, parent)`.
Assign to a mesh component: ObjectTools `set_properties` on the component (`OverrideMaterials` — check list_properties) or
StaticMeshTools for the mesh asset itself.

---

## StaticMeshTools (`editor_toolset.toolsets.static_mesh.StaticMeshTools`) — 15 tools (brief)

All take `mesh: ref<StaticMesh>` (asset-level edits; affect every user of the mesh — do not run on template/engine meshes).
- Materials: `get_material_slots(mesh) -> [str]`, `get_material(mesh, slot_name) -> ref`, `set_material(mesh, slot_name, material: ref<MaterialInterface>) -> bool`.
  (Docstring mentions a `set_component_material_override` tool for per-instance overrides; it is not in this toolset — use ObjectTools on the component.)
- Info: `get_bounds(mesh) -> Box`, `get_vertex_count(mesh, lod_index?: int =0)`, `get_triangle_count(mesh, lod_index?)`, `get_lod_count(mesh)`, `get_lod_thresholds(mesh) -> [number]`.
- LOD: `generate_lods(mesh, triangle_percents: [number]) -> int`, `remove_lods(mesh) -> bool`, `set_lod_thresholds(mesh, thresholds: [number]) -> bool`.
- Collision: `generate_convex_collisions(mesh, hull_count?: int =4, max_hull_verts?: int =16, hull_precision?: int =100000) -> bool`, `remove_collisions(mesh) -> bool`.
- Nanite: `is_nanite_enabled(mesh) -> bool`, `set_nanite_enabled(mesh, enabled: bool)`.
- Import: `import_file(folder_path, asset_name, source_file: str (abs), import_materials?: bool =false, import_textures?: bool =false, combine_meshes?: bool =true) -> [ref]`.

---

## GameplayTagsToolset (`GameplayTagsToolset.GameplayTagsToolset`) — 6 tools

camelCase args. Project tags live in `SoulCombat/Config/DefaultGameplayTags.ini` (already defined).
- `ListTags(parentTag: str) -> [str]` — `""` = all; `"State"` = descendants.
- `GetTagInfo(tagName: str) -> {comment, source, children[]}` — script error if tag missing.
- `FindReferencersByTag(tagName) -> [package paths]`.
- `AddTag(tagName: str, tagSource: str, comment?: str)` — `tagSource ""` = default INI. **Pass `comment` explicitly**: the schema
  default for `comment` is the whole C++ doc comment string (bug) and would be written into the INI.
  Docstring: call only with explicit user permission.
- `RemoveTag(tagName)`, `RenameTag(oldTagName, newTagName)` — explicit user permission only.
Using tags in BP: GameplayTag variables via `add_struct_variable(struct_type=/Script/GameplayTags.GameplayTag)`; pin values via
`set_pin_value` (format probably `(TagName="State.Dead")` — untested).

---

## GameplayCueToolset (`GASToolsets.GameplayCueToolset`) — 8 tools

camelCase args.
- `ListCues(parentTag: str) -> [str]` — `""` = everything under `GameplayCue`.
- `GetCueInfo(cueTag: str) -> {tag, notifyAssetPath, notifyType: Static|Actor|None}` — script error if tag missing.
- `FindCueNotifyAssets(parentTag: str) -> [{cueTag, assetPath, assetName, notifyType}]`.
- `FindCueTagsWithoutNotifies() -> [str]`.
- `CreateCueNotifyAsset(cueTag: str, packagePath: str, assetName: str, bIsActor: bool) -> str` — creates a GCN Blueprint
  (`bIsActor` false = GameplayCueNotify_Static, true = GameplayCueNotify_Actor). Tag must exist. Returns object path or `""`.
  e.g. `{"cueTag":"GameplayCue.Hit","packagePath":"/Game/_Scratch","assetName":"GCN_Hit","bIsActor":false}`.
  Then implement `OnExecute` via BlueprintTools (`add_function_graph`/`add_event` override + DSL). Docstring: user permission.
- `AddCueTag(cueTag: str, comment?: str) -> bool` — must start with `GameplayCue.`; pass `comment` explicitly (same default-comment bug
  as AddTag). `RemoveCueTag(cueTag) -> bool`. Both: user permission.
- `ExecuteCueOnSelectedActor(cueTag, normalizedMagnitude: number, location: {x,y,z}, normal: {x,y,z}) -> bool` — preview on the
  editor-selected actor (needs PIE or configured cue manager for visible result).

---

## AttributeSetToolset (`GASToolsets.AttributeSetToolset`) — 2 tools (read-only)

- `FindAttributeSetClasses() -> [{className, assetPath ("" for native), attributes: [{attributeName, fullName, setClassName}]}]`.
- `ListAttributes(className: str) -> [{attributeName, fullName, setClassName}]` — className with U prefix per the docstring,
  e.g. `{"className":"USCAttributeSet"}` (if that fails try `SCAttributeSet`). Script error if not an AttributeSet.
No tool creates AttributeSets or GameplayEffects specifically: GE assets = BlueprintTools `create` with parent
`/Script/GameplayAbilities.GameplayEffect`, then ObjectTools on the CDO (Modifiers array, DurationPolicy, etc.).

---

## AbilitySystemInspectorToolset (`GASToolsets.AbilitySystemInspectorToolset`) — 4 tools (runtime read-only)

All take `actor: ref<Actor>` (an actor with an ASC; in PIE use the PIE-world actor ref from SceneTools `find_actors` during PIE —
untested how PIE actors are addressed). Script error if actor null or no ASC.
- `GetGrantedAbilities(actor) -> [{abilityName, level, bIsActive}]`.
- `GetAttributeValues(actor) -> [{attributeName, fullName, setClassName, baseValue, currentValue}]`.
- `GetActiveTags(actor) -> [str]` — loose + effect-granted tags (e.g. check `State.Dead`, `Cooldown.Skill.1`).
- `GetActiveEffects(actor) -> [{effectName, stackCount, totalDuration, remainingDuration, grantedTags[]}]` (-1 = infinite).
Main use: verification during PIE (damage applied, cooldown tag present, abilities granted from SCAbilitySet).

---

## EditorAppToolset (`EditorToolset.EditorAppToolset`) — 21 tools

camelCase args.

PIE
- `StartPIE(options: {bSimulate: bool, playMode: EPlayModeType, warmupSeconds: number, startTransform?: ToolsetTransform})` —
  returns after BeginPlay + warmup. Errors if a session already runs. Example:
  `{"options":{"bSimulate":false,"playMode":"PlayMode_InViewPort","warmupSeconds":2}}`. Out-of-process modes are downgraded to InViewPort.
  playMode enum: PlayMode_InViewPort, PlayMode_InEditorFloating, PlayMode_InMobilePreview, PlayMode_InTargetedMobilePreview,
  PlayMode_InVulkanPreview, PlayMode_InNewProcess, PlayMode_InVR, PlayMode_Simulate, PlayMode_QuickLaunch.
- `StopPIE()` — errors if nothing running. `IsPIERunning() -> bool`.
- No tool to inject player input during PIE here (see SlateInspectorToolset for UI input; gameplay input untested).

Screenshots / images (base64 PNG in `returnValue.image.data` / `returnValue.data`; large — verification only)
- `CaptureViewport(captureTransform?: ToolsetTransform, annotations?: {gridSpacing, gridExtent, gridHeight, maxLabelDistance, classFilter, maxLabels}, bShowUI?: bool =false) -> {image, cameraLocation, cameraRotation, cameraFOV, grid, labeledActors[]}` —
  level viewport; optional grid + actor label overlay (all six annotation fields required if annotations passed; classFilter may need `null`).
- `CaptureEditorImage() -> {mimeType, data}` — whole editor as the user sees it.
- `CaptureAssetImage(assetPath: str) -> {mimeType, data}` — thumbnail (meshes, anims, montages, materials...).

Selection / navigation
- `SelectActors(actors: [ref<Actor>])`, `GetSelectedActors() -> [ref<Actor>]`.
- `SelectAssets(assetPaths: [str])`, `GetSelectedAssets() -> [str]`.
- `OpenEditorForAsset(assetPath: str)` — open asset editor (e.g. BP editor). `GetOpenAssets() -> [str]`.
- `SetContentBrowserPath(path: str)`, `GetContentBrowserPath() -> str`.

Camera / viewport
- `GetCameraTransform() -> ToolsetTransform`, `SetCameraTransform(transform: ToolsetTransform)`.
- `FocusOnActors(actors: [ref<Actor>])` — not during PIE.
- `GetVisibleActors() -> [ref<Actor>]`.
- `WorldPosToScreenCoords(position: {x,y,z}) -> {x,y}` (normalized), `ScreenCoordsToWorld(coords: {x,y}, traceDistance?: number =100000) -> {x,y,z}`.

Console
- `SearchCVars(name: str) -> str (JSON)` — search only; **no set-cvar / exec-console-command tool** in this toolset.

---

## LogsToolset (`EditorToolset.LogsToolset`) — 4 tools

camelCase args. **Gotcha: `category` defaults to `"LogsToolset"`** (schema default) — always pass it explicitly (`""` = all categories).
- `GetLogEntries(pattern: str, category?: str, maxEntries?: int =1000) -> [str]` — current session log; `pattern` regex (`""` = any);
  entries from the end. e.g. `{"category":"LogBlueprintUserMessages","pattern":"","maxEntries":50}` for PrintString output,
  `{"category":"","pattern":"Error|Warning","maxEntries":100}`.
- `GetLogCategories(filter: str) -> [str]`.
- `GetVerbosity(category?) -> str`, `SetVerbosity(verbosity: NoLogging|Fatal|Error|Warning|Display|Log|Verbose|VeryVerbose, category?)`.

---

## ConfigSettingsToolset (`ConfigSettingsToolset.ConfigSettingsToolset`) — 8 tools

Project Settings / Editor Preferences sections (container -> category -> section). camelCase args. Writes go to Default*.ini.
- `ListContainers() -> [str]` (e.g. `Editor`, `Project`), `ListCategories(containerName) -> [str]` (e.g. `Engine`, `Game`, `Project`),
  `ListSections(containerName, categoryName) -> [str]` (e.g. `General`, `Maps`, `Input`, `Collision`?).
- `GetSectionSchema(containerName, categoryName, sectionName) -> str (JSON schema)`.
- `GetSectionPropertyValues(containerName, categoryName, sectionName, propertyNames: [str]) -> str (JSON)`.
- `SetSectionProperties(containerName, categoryName, sectionName, propertiesJson: str) -> bool` — JSON **string** in the same
  format GetSectionPropertyValues returns; saves automatically. Raises on failure.
- `SaveSection(...)  -> bool`, `ResetSectionToDefaults(...) -> bool`.
Uses: GameMode/default map (Project/Project/Maps & Modes?), collision channels, Enhanced Input default classes. Verify names with List*.

---

## ProgrammaticToolset (`editor_toolset.toolsets.programmatic.ProgrammaticToolset`) — 2 tools

**Sandboxed tool-orchestration Python, NOT the editor Python API.** Allowed imports only: `math, json, re, datetime, time, copy`.
No `import unreal`, so it cannot do anything the other tools cannot do (no enum/struct/montage/level creation via Python).
Use it only to batch many tool calls in one round trip (e.g. add 10 variables, set many properties).
- `get_execution_environment() -> {instructions, supported_modules[], language}` — must be called once per conversation before
  `execute_tool_script` (per docstring).
- `execute_tool_script(script: str) -> str (JSON of run()'s dict)` — script must define `run() -> dict`. Inside, call
  `execute_tool("<FULL dotted tool name>", json_string_input)` which returns a dict-like result (`["returnValue"]`) and raises
  RuntimeError on failure. Full names = `<toolset_name>.<tool_name>`, e.g.
  `editor_toolset.toolsets.blueprint.BlueprintTools.add_variable`, `EditorToolset.EditorAppToolset.GetSelectedActors`.
  Example:
  ```python
  import json
  BP = {"refPath": "/Game/_Scratch/BP_Test.BP_Test"}
  def add_var(name, t):
      return execute_tool("editor_toolset.toolsets.blueprint.BlueprintTools.add_variable",
                          json.dumps({"blueprint": BP, "name": name, "type_name": t}))
  def run():
      for n, t in [("Speed", "float"), ("bDead", "bool")]:
          add_var(n, t)
      return {"ok": True}
  ```
  Caveat: this still counts as many MCP operations in one call; one failure aborts the rest of the script (partial state).
  Record uses as "Python" per CLAUDE.md.

---

## SlateInspectorToolset (`SlateInspectorToolset.SlateInspectorToolset`) — 14 tools

Playwright-style editor UI automation (Slate). Refs are strings from `Snapshot`. camelCase args. This is the **generic fallback**
for editor features with no dedicated tool (context menus, dialogs, Class Settings, asset editors) and for closing modal windows.
Workflow: `Windows(action="list")` -> `Observe(ref=<window/panel>)` -> `Snapshot(ref=...)` -> `Click/Type/SelectOption/...` -> `Unobserve`.
- `Windows(action?: "list"|"select"|"close" ="list", index?: int =-1) -> str (JSON)` — list/front/close top-level windows (can close a modal).
- `Snapshot(ref: str ("" = all windows), maxDepth?: int =30, bIncludeSourceLocations?: bool =false) -> str` — accessibility tree with refs. Can be large.
- `Observe(ref: str, maxDepth?: int =30) -> str (identifier)` / `Unobserve(identifier) -> bool` / `ListObservers() -> str`.
- `Click(ref, button?: left|right|middle ="left", doubleClick?: bool =false, modifiers?: {bShift,bCtrl,bAlt,bCmd}) -> bool`.
- `Type(ref, text: str, submit?: bool =false) -> bool` — focuses then types char by char.
- `PressKey(key: str) -> bool` — on focused widget, e.g. `"Enter"`, `"Ctrl+S"`, `"C"` (comment selected nodes in graph editor — untested).
- `SelectOption(ref, value: str) -> bool` — combobox by exact text.
- `FillForm(fields: [{ref, value, fieldType: textbox|checkbox|combobox}]) -> bool`.
- `Hover(ref) -> bool`, `Drag(startRef, endRef, modifiers?) -> bool`.
- `WaitFor(text: str, textGone: str) -> bool` — single non-blocking check; poll.
- `Screenshot(ref: str ("" = active window)) -> {mimeType, data}` — editor UI screenshot (docstring refers to a
  `SceneTools.take_screenshot` that does not exist; for 3D use EditorAppToolset.CaptureViewport).
Caveat: UI-driven steps are brittle (refs change, layout-dependent). Does not drive in-game (PIE) gameplay input as documented.

---

## AgentSkillToolset (`ToolsetRegistry.AgentSkillToolset`) — 4 tools

Skills are assets (Blueprint classes, path like `/Game/Skills/MySkill.MySkill_C`) with a description + markdown `instructions`.
Digest of the relevant skills: `docs/mcp/skills.md`.
- `ListSkills() -> map<skillPath, description>`.
- `GetSkills(skillPaths: [str]) -> map<skillPath, {instructions}>`.
- `CreateSkill(folderPath: str, assetName: str, description: str, details: {instructions: str}) -> str (skill class path or "")` — user permission.
- `UpdateSkill(skillPath: str, description: str, details: {instructions}) -> bool` — user permission.

---

## NiagaraToolset_Component (`NiagaraToolsets.NiagaraToolset_Component`) — 4 tools (brief)

For a NiagaraComponent (add it with ActorTools `add_component`, component_type `/Script/Niagara.NiagaraComponent`).
- `SetSystem(niagaraComponent: ref<NiagaraComponent>, system: ref<NiagaraSystem>, bResetExistingOverrideParameters: bool)` — use instead of setting `Asset` directly.
- `GetUserVariables(component) -> [NiagaraExt_VariableInst]`.
- `GetVariable(component, var: {name: str, type: {classStructOrEnum: ref}}) -> NiagaraExt_VariableInst`.
- `SetVariable(component, variable: {name, type: {classStructOrEnum: ref}, value: {struct: ref<ScriptStruct>, value: <typed>}})` —
  e.g. float: `{"name":"User.Scale","type":{"classStructOrEnum":{"refPath":"/Script/Niagara.NiagaraFloat"}},"value":{"struct":{"refPath":"/Script/Niagara.NiagaraFloat"},"value":{"value":2.0}}}`
  (shape from schema; untested). Bool uses int -1/0. Also Vector/LinearColor/Position/Object/Enum/DataInterface wrappers.
For hit FX in combat, simpler path: BP graph node `SpawnSystemAtLocation` in DSL/GameplayCue instead of a component.

---

## SkeletalMeshTools (`editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools`) — 21 tools (extra, brief)

`mesh: ref<SkeletalMesh>`. Read tools are safe on template meshes; **write tools (sockets, materials, physics asset) modify the
template asset — duplicate the mesh into `/Game/_Scratch` first or avoid.**
- Bones: `get_bone_names(mesh) -> [str]`, `get_bone_parent(mesh, bone_name) -> str`, `get_bone_children(mesh, bone_name) -> [str]`, `get_skeleton(mesh) -> ref<Skeleton>`.
- Sockets: `get_socket_names(mesh)`, `get_socket_bone(mesh, socket_name)`, `get_socket_transform(mesh, socket_name)`,
  `add_socket(mesh, socket_name, bone_name) -> ref<SkeletalMeshSocket>`, `set_socket_transform(mesh, socket_name, transform)`, `rename_socket(mesh, old_name, new_name)`, `remove_socket(mesh, socket_name)`.
- Materials: `get_material_slots`, `get_material(mesh, slot_name)`, `set_material(mesh, slot_name, material)`.
- Other: `get_physics_asset`, `assign_physics_asset(mesh, physics_asset)`, `get_morph_target_names`, `get_bounds`, `get_section_count/get_vertex_count(mesh, lod_index?=0)`, `get_lod_count`,
  `import_file(folder_path, asset_name, source_file, skeleton?, import_materials?, import_textures?, import_animations?, create_physics_asset?)`.
**No toolset in this editor covers AnimMontage / AnimSequence / AnimBlueprint / notifies / montage sections** (checked list_toolsets:
only ControlRig and Sequencer animation toolsets exist).

---

## Editor state observed during this survey (read-only calls)

- Current level: `/Game/ThirdPerson/Lvl_ThirdPerson` (SceneTools `get_current_level`).
- Maps in /Game (AssetTools `find_assets` asset_type `/Script/Engine.World`): `/Game/ThirdPerson/Lvl_ThirdPerson`,
  `/Game/Variant_Platforming/Lvl_Platforming`, `/Game/Variant_Combat/Lvl_Combat`.
- Montages in /Game (asset_type `/Script/Engine.AnimMontage`): `/Game/Variant_Combat/Anims/AM_ComboAttack`,
  `/Game/Variant_Combat/Anims/AM_ChargedAttack`, `/Game/Variant_Platforming/Anims/AM_Dash`,
  `/Game/Characters/Mannequins/Anims/Pistol/MM_Pistol_Fire_Montage`.

## Capability check (step 4) — status from documentation only

| Capability | Status | How / notes |
|---|---|---|
| Set node positions | WORKS (doc) | BlueprintTools `set_node_position {node:{refPath}, pos:{x,y}}`; also `create_node.pos`, `add_event.position`. Read positions via `get_node_infos` (`position`). |
| Create comment boxes | UNTESTED | No dedicated tool; DSL has no comment syntax (`;` is a source comment). Candidates: `find_node_types(graph, "Comment", [])` on a _Scratch BP to see if an "Add Comment" action type_id exists for `create_node`; then size/text via ObjectTools on the node (`NodeComment`, `NodeWidth`, `NodeHeight`?). Fallback: SlateInspector (select nodes, `PressKey "C"`). |
| Auto-arrange / format graph | WORKS (doc) | BlueprintTools `arrange_nodes {nodes:[{refPath},...]}` — left-to-right by exec/data flow; external links are anchors. Get node list via `find_nodes(graph, "", null, false)`. |
| Add interface to a BP | UNTESTED | No tool (BlueprintTools has none; `list_events/list_functions` only *read* interface members). Candidates: ObjectTools `set_properties` on the Blueprint asset's `ImplementedInterfaces` (list_properties first; may not create stub graphs), or SlateInspector on Class Settings > Implemented Interfaces > Add. Creating a Blueprint Interface asset also has no documented tool (maybe BlueprintTools `create` with an interface class — unknown). Alternative design: event dispatchers / GameplayTags / GAS events instead of interfaces. |
| Class-reference (TSubclassOf) variables | UNTESTED | `add_variable` supports only bool/int/float/byte/string/name/text/Vector/Rotator/Transform/Vector2D/LinearColor; `add_object_variable` = object reference; `add_struct_variable` = struct. No class-ref option. Candidate: `add_object_variable(object_class=/Script/CoreUObject.Class)` (gives a UClass object ref, not a true class pin — verify). Setting existing TSubclassOf *properties* (e.g. SCAbilitySet `Abilities[].Ability`, GE classes) via ObjectTools `set_properties` with class path strings should work (untested format). Changing var type in UI risks a modal. |
| Map / Set variables | WORKS (doc) | `container_type: "SET"` or `"MAP"` on add_variable / add_object_variable / add_struct_variable / add_*function_param. **MAP key type is always string**; value type = the given type. |
| Create enums / structs (UserDefinedEnum/Struct) | IMPOSSIBLE (no tool) | No toolset creates UserDefinedEnum/UserDefinedStruct; ProgrammaticToolset is sandboxed (no `unreal` module). Only route is SlateInspector UI automation (Content Browser > Blueprint > Enumeration/Structure + editing rows) — untested and brittle. Recommended: avoid; use GameplayTags, Name/int, or the C++ types already in SCAttributeSet/SCAbilitySet. Existing structs can be used via `add_struct_variable`. |
| Create levels | WORKAROUND (doc) | No create-level tool. AssetTools `duplicate {"path":"/Game/ThirdPerson/Lvl_ThirdPerson","new_path":"/Game/_Scratch/L_Test"}` then SceneTools `load_level {"level_path":"/Game/_Scratch/L_Test"}` (make sure current level is not dirty first: modal risk). Clear/populate with `find_actors` / `remove_from_scene` / `add_to_scene_from_class`. |
| Create montages | WORKAROUND (doc) | No anim toolset. AssetTools `duplicate` an existing montage (e.g. `/Game/Variant_Combat/Anims/AM_ComboAttack` -> `/Game/_Scratch/AM_Attack`). Pointing it to another AnimSequence would need ObjectTools on `SlotAnimTracks` (untested). |
| Edit montage notifies / sections | UNTESTED | No dedicated tool. Candidates: ObjectTools `list_properties`/`set_properties` on the montage (`CompositeSections`, `Notifies`, `SlotAnimTracks`) — nested arrays of instanced structs, format unknown; or SlateInspector in the montage editor. Alternative design: use AnimNotify-free timing (GAS WaitDelay / PlayMontageAndWait + timers) or keep notifies already present in the duplicated template montage (read them with get_properties). |
| Bind widget events | WORKS (doc) | UMGToolSet `ToggleWidgetAsVariable` then `BindToEventProperty {widgetBlueprint, eventName:"OnClicked", propertyName:"<widget var>", propertyClass:{"refPath":"/Script/UMG.Button"}}`; implement handler via BlueprintTools on the WBP EventGraph. Component delegates on actor BPs: BlueprintTools `add_component_bound_event`. Dispatcher binding: `create_node` + `set_create_event_function`. |
| Run PIE | WORKS (doc) | EditorAppToolset `StartPIE {"options":{"bSimulate":false,"playMode":"PlayMode_InViewPort","warmupSeconds":2}}`, `IsPIERunning`, `StopPIE`. Don't edit assets while PIE runs. No documented tool to inject gameplay input in PIE. Read results with LogsToolset `GetLogEntries` and AbilitySystemInspectorToolset. |
| Take screenshots | WORKS (doc) | EditorAppToolset `CaptureViewport {}` (3D viewport, optional annotations), `CaptureEditorImage {}` (whole editor), `CaptureAssetImage {"assetPath":...}` (thumbnail); SlateInspector `Screenshot {"ref":""}` (active editor window). Base64 PNG — large; verification only. |

## Global gotchas (from docs)

- Arg naming differs per toolset: editor_toolset.* = snake_case; UMG/GAS/EditorApp/Logs/Config/Slate/Tags = camelCase.
- `tool_name` in `call_tool` is the short name; inside ProgrammaticToolset scripts use the full dotted name.
- Object args are always `{"refPath": ...}`; AssetTools/EditorApp asset args are plain path strings.
- JSON-string args (not objects): ObjectTools `set_properties.values`, DataTableTools `set_rows.values`, ConfigSettings `propertiesJson`.
- Never `save_assets([])` (saves everything dirty, incl. templates). Always explicit `/Game/_Scratch/...` paths.
- `find_node_types` may dirty the BP it runs on; only run on _Scratch BPs.
- `remove_function_graph` closes the BP editor window if open.
- `write_graph_dsl` compiles the BP; other graph edits need `compile_blueprint`.
- LogsToolset `category` default is `"LogsToolset"`; AddTag/AddCueTag `comment` default is a raw doc comment — pass both explicitly.
- Several docstrings reference tools that don't exist (`SceneTools.take_screenshot`, `set_component_material_override`, `AssetTools.save_asset`, `GetTaggedWidgetDescription`) — use the names listed here.
