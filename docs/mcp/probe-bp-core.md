# Probe: Blueprint core capabilities (UE 5.8.2, Unreal MCP)

Scratch assets: `/Game/_Scratch/BP_ProbeActor` (+ helpers). Toolset short names as in `toolsets.md`
(BlueprintTools = `editor_toolset.toolsets.blueprint.BlueprintTools`, ObjectTools = `editor_toolset.toolsets.object.ObjectTools`, ...).
Status legend: WORKS / WORKAROUND / IMPOSSIBLE / UNTESTED.
`BP` below = `{"refPath":"/Game/_Scratch/BP_ProbeActor.BP_ProbeActor"}`.

## General gotchas found while probing

- Errors from BlueprintTools come back as MCP errors with a readable message (e.g. `Unknown type "GameplayTag". Supported: ...`),
  success usually returns `{"returnValue": null}`.
- ProgrammaticToolset `execute_tool_script`: a **schema validation error** (e.g. wrong ref class for `struct_type`) aborts the whole
  script and is NOT catchable by `try/except`. Runtime errors are catchable, but if any tool call inside the script raised
  (even caught), the MCP result is replaced by the concatenated error messages and the returned dict is lost. Calls before/after
  still executed. => In scripts, only batch calls you expect to succeed; probe unknowns one by one.
- ObjectTools on a Blueprint ref **and** on its `_C` class ref both resolve to the CDO (`Default__BP_X_C`). The UBlueprint asset
  object itself (NewVariables, etc.) is not reachable -> no variable metadata editing through ObjectTools.
- ObjectTools only exposes "editable" properties. On graph nodes (`K2Node_FunctionEntry`) `list_properties` shows only
  `errorMsg`; `NodePosX`, `NodeComment`, `ExtraFlags`, `MetaData` -> `the following properties could not be read`.
- `get_node_type_pins` creates a transient node (ref like `...EventGraph.K2Node_VariableGet_0`) but does not leave it in the graph
  (verified with `find_nodes`). Handy to check a variable's real pin type: `get_node_type_pins(graph, "Variables|Default|Get<Var>")`
  -> `output_pins[0].type_id` e.g. `"Actor Object Reference"`, `"Map of Strings to Gameplay Tag Structures"`.
- `list_properties` on an actor CDO dumps ~40 KB (all AActor props). Prefer `get_properties` with explicit names.

## 1. Variables

| What | Status | Exact call (BlueprintTools unless noted) |
|---|---|---|
| bool/int/float/byte/name/string/text | WORKS | `add_variable {"blueprint":BP,"name":"IntVar","type_name":"int"}` (type_name: `bool,int,float,byte,name,string,text`). Undocumented alias: `"real"` -> float (double). Case-insensitive for structs (`"vector"` ok). `double`, `int64`, `object`, `class`, `GameplayTag` -> error `Unknown type "X". Supported: bool, int, float, byte, name, string, text, Vector, Rotator, Transform, Vector2D, LinearColor.` |
| Vector/Rotator/Transform/Vector2D/LinearColor | WORKS | `add_variable` with `type_name` `Vector`/`Rotator`/`Transform`/`Vector2D`/`LinearColor` |
| GameplayTag / GameplayTagContainer / any USTRUCT | WORKS | `add_struct_variable {"blueprint":BP,"name":"TagVar","struct_type":{"refPath":"/Script/GameplayTags.GameplayTag"}}` (`.../GameplayTagContainer`, `/Script/Engine.HitResult`) |
| Object ref (Actor, UserWidget, BP class) | WORKS | `add_object_variable {"blueprint":BP,"name":"ActorRef","object_class":{"refPath":"/Script/Engine.Actor"}}`; UserWidget `/Script/UMG.UserWidget`; BP type `/Game/_Scratch/BP_ProbeActor.BP_ProbeActor_C` (pin type `BP Probe Actor Object Reference`) |
| Class ref (TSubclassOf) | see section 1b | `add_object_variable` with `object_class` `/Script/CoreUObject.Class` or `/Script/Engine.BlueprintGeneratedClass` **silently creates an `Integer` variable** (no error). Same for `add_object_function_param`. |
| Arrays / Sets | WORKS | add `"container_type":"ARRAY"` or `"SET"` to add_variable / add_struct_variable / add_object_variable |
| Map | WORKAROUND | `"container_type":"MAP"` -> key is **always String** (`Map of Strings to Gameplay Tag Structures`). GameplayTag->int map impossible directly; use String key (tag name) or two parallel arrays. |
| Local variable | WORKS | same add_* tools with `"graph":{"refPath":".../BP_ProbeActor:CalcDamage"}`; `list_variables {"blueprint":BP,"graph":G}`. DSL references it as `Variables|Default|GetLocalTemp` / `SetLocalTemp`. |
| Instance editable | WORKS | `set_variable_instance_editable {"blueprint":BP,"variable_name":"FloatVar","instance_editable":true}` |
| Category | WORKS | `set_variable_category {..., "variable_name":"FloatVar","category":"Probe|Stats"}`; `get_variable_category` -> `"Probe|Stats"` (unset = `"Default"`) |
| Replication | WORKS | `set_variable_replication {..., "replication":"RepNotify"}` auto-creates function `OnRep_IntVar` |
| Default values | WORKS | compile first, then ObjectTools `set_properties {"instance":BP,"values":"<JSON string>"}` -> `true`. Formats that round-tripped (get_properties): bool `true`, int `7`, float `2.5`, name/string/text `"Hello"`, Vector `{"x":1,"y":2,"z":3}`, Rotator `{"pitch":10,"yaw":20,"roll":30}`, Transform `{"location":{..},"rotation":{..},"scale":{..}}`, LinearColor `{"r":1,"g":0,"b":0,"a":1}`, array `[1,2,3]`, set `["A","B"]`, map `{"one":1}`, GameplayTag `{"tagName":"State.Dead"}`, TagContainer `{"gameplayTags":[{"tagName":"State.Dead"}]}`, map of tags `{"atk":{"tagName":"InputTag.Attack"}}`. Property names are case-insensitive (list shows camelCase `intVar`, `IntVar` works). |
| Expose on spawn / tooltip (Description) / Private / BlueprintReadOnly | WORKAROUND (UI) | no BlueprintTools tool; ObjectTools cannot reach the UBlueprint variable descriptions. SlateInspector: select the variable in My Blueprint (see 1b), then in the Details panel (`generic "List"` under the Details tab) `Click` the row checkbox (`generic "Expose on Spawn"` -> `checkbox`) -> became `[checked]`; `Type {"ref":<Description textbox>,"text":"Enemy class to spawn","submit":true}` -> true. **The Details panel rebuilds after every edit -> re-snapshot before the next click.** Instance editable / category: use the BlueprintTools tools instead. |
| Rename variable | WORKAROUND (UI) | no rename tool (remove+add loses references). SlateInspector: My Blueprint `treeview "List"` -> `Click` the variable's `text` -> `PressKey {"key":"F2"}` -> re-snapshot (row now has a focused `textbox`) -> `Type {"ref":<inner textbox>,"text":"EnemyClass","submit":true}`. Verified with `list_variables` ("Enemy Class" -> "EnemyClass"); existing Get nodes followed the rename. |

### 1b. Class references (TSubclassOf), maps with non-string keys — WORKAROUND verified

No tool creates them (see table). What works:
1. Paste (recipe A in section 5: PowerShell `Set-Clipboard` + SlateInspector click in graph + `PressKey Ctrl+V`) a `K2Node_VariableGet`
   for a NOT-yet-existing member whose output pin has the wanted type. The paste keeps the node (it does not create the variable):
   ```
   Begin Object Class=/Script/BlueprintGraph.K2Node_VariableGet Name="K2Node_VariableGet_701"
      VariableReference=(MemberName="EnemyClass",bSelfContext=True)
      NodePosX=0
      NodePosY=0
      CustomProperties Pin (PinId=<32 hex>,PinName="EnemyClass",Direction="EGPD_Output",PinType.PinCategory="class",PinType.PinSubCategory="",PinType.PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.Actor'",PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,PersistentGuid=00000000000000000000000000000000,bHidden=False,bNotConnectable=False,bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=False,bOrphanedPin=False,)
   End Object
   ```
   Other pin types used: GE class `PinSubCategoryObject="/Script/CoreUObject.Class'/Script/GameplayAbilities.GameplayEffect'"`;
   Map GameplayTag->int: `PinCategory="struct",PinSubCategoryObject="/Script/CoreUObject.ScriptStruct'/Script/GameplayTags.GameplayTag'",ContainerType=Map,PinValueType=(TerminalCategory="int",TerminalSubCategory="",TerminalSubCategoryObject=None,bTerminalIsConst=False,bTerminalIsWeakPointer=False,bTerminalIsUObjectWrapper=False)`;
   class array: `PinCategory="class"... ContainerType=Array`. (Generator: python in scratchpad, see `vars.t3d` approach.)
2. Right-click the pasted node's pin label (`Click {"ref":<text "Enemy Class">,"button":"right"}`) -> new untitled window -> `Snapshot` it ->
   `Click` `text "Promote to Variable"`. A member variable of exactly that type is created (it also adds a `SET` node — delete it and the
   pasted Get node with `delete_node`).
3. The promoted name uses the pin display name WITH spaces ("Enemy Class", "Tag Counts"); DSL ids strip spaces
   (`Variables|Default|GetTagCounts`). Rename with F2 (table above) if you need a clean name.
Verified types: `get_node_type_pins "Variables|Default|GetEnemyClass"` -> `Actor Class Reference`; `...GetTagCounts` ->
`Map of Gameplay Tag Structures to Integers`. Defaults via ObjectTools: `{"EnemyClass":{"refPath":"/Game/_Scratch/BP_ProbeOther.BP_ProbeOther_C"}}`
-> true and read back; `{"Tag Counts":{"State.Dead":3}}` -> true, reads back as `{"(TagName=\"State.Dead\")":3}`.
Alternatives without UI: store a class inside a USTRUCT that has a TSubclassOf member (e.g. `/Script/SoulCombat.SCAbilityGrant`) via
`add_struct_variable`, or keep class refs in a DataAsset (`SCAbilitySet`) and read them in the graph.

## 2. Functions

| What | Status | How |
|---|---|---|
| Create function | WORKS | `add_function_graph {"blueprint":BP,"graph_name":"CalcDamage"}` -> `{"refPath":".../BP_ProbeActor:CalcDamage"}` |
| Inputs / outputs | WORKS | `add_function_param {"graph":G,"param_name":"BaseDamage","param_type":"float","input_param":true}` (returns entry-node PinID); outputs `"input_param":false` (creates `K2Node_FunctionResult`). Object: `add_object_function_param {..."object_class":{"refPath":"/Script/Engine.Actor"}}`; struct/array: `add_struct_function_param {..."struct_type":{"refPath":"/Script/GameplayTags.GameplayTag"},"container_type":"ARRAY"}`. `remove_function_param {"graph":G,"param_name":"X","input_param":true}` works. Class-typed param (`/Script/CoreUObject.Class`) -> silently `Integer`. |
| Local variables | WORKS | `add_variable {"blueprint":BP,"name":"LocalTemp","type_name":"float","graph":G}` |
| Body via DSL | WORKS | `write_graph_dsl {"graph":G,"code":"(fn CalcDamage (BaseDamage Multiplier Target Tags)\n (Variables|Default|SetLocalTemp (* BaseDamage Multiplier))\n (bind t (Variables|Default|GetLocalTemp))\n (return t (> t 100.0)))"}` — `(return a b)` fills outputs in declaration order. |
| Pure / const / category / tooltip / access specifier / keywords | see section "UI-only" | no tool; DSL has no attribute syntax (`(fn X (A) :pure true ...)` -> `Statement must be a list, got: ':pure'`); ObjectTools cannot read `K2Node_FunctionEntry.ExtraFlags/MetaData`. |
| Macros (user macro graphs) | IMPOSSIBLE (tools) | no add_macro_graph tool; `add_function_graph` always makes a function. Engine macros (ForEachLoop, IsValid, ...) can be *used* (`Utilities|IsValid`, `Utilities|FlowControl|ForLoop`). |

DSL function gotchas:
- Params must exist before writing: `(fn PureTest (A) ...)` with no param A -> `Function parameter(s) not found in graph: ['A']`.
- **Outputs must exist before writing**: `(return (* A 2))` with no output param returns `null` (success) but writes NOTHING (silent failure). Always `add_function_param ... "input_param":false` first and re-read with `read_graph_dsl`.
- **Rewriting a function graph does not delete the previous body**: entry exec is rewired to the new chain, the old `FunctionResult`/math nodes stay as orphans. `read_graph_dsl` hides orphans (only follows exec from the entry). Before re-writing a function: `find_nodes(G,"")` and `delete_node` everything except `K2Node_FunctionEntry_0` (or delete orphans afterwards).
- Integer literal in math (`(* A 2)`) becomes a separate `Math|Integer|MakeLiteralInt` node (float `10.0` -> `Math|Float|MakeLiteralFloat` node) instead of a pin default. Named pin args (`:Amount 5.0`) become pin defaults (no extra node).

## 3. Events, dispatchers, component events

| What | Status | How |
|---|---|---|
| Custom event (no params) | WORKS | `add_event {"blueprint":BP,"event_name":"OnProbeHit","position":{"x":0,"y":600}}` -> `K2Node_CustomEvent_0`. DSL head for custom events is `Custom|<Name>`: `(event Custom|OnProbeHit ...)`. `(event OnProbeHit ...)` -> `AssertionError: The node could not be created / AddEvent|OnProbeHit does not exist`. |
| Custom event WITH params | WORKAROUND | No param tool for events (`add_function_param` on the event node -> `... is not valid EdGraph for property 'graph'`); DSL param list on a custom event is silently ignored. Recipe: create an event dispatcher with the wanted signature (`add_event_dispatcher` + `add_*_function_param` on the returned graph, compile), then `create_node {"graph":EventGraph,"type_id":"Default|EventDispatcher<Disp>","pos":{...}}` -> standalone custom event `<Disp>_0` with the same params (name auto-generated, not renamable by tools). Alternatively `Default|Assign<Disp>` creates a Bind node + event `<Disp>_Event`. |
| Event dispatcher with params | WORKS | `add_event_dispatcher {"blueprint":BP,"name":"OnDamaged"}` -> graph ref `.../BP_ProbeActor:OnDamaged`; then `add_function_param {"graph":<that>,"param_name":"Amount","param_type":"float","input_param":true}`, `add_object_function_param`, `add_struct_function_param`. Compile. Node types then available: `Default|BindEventtoOnDamaged`, `Default|AssignOnDamaged`, `Default|CallOnDamaged`, `Default|UnbindEventfromOnDamaged`, `Default|UnbindallEventsfromOnDamaged`, `Default|EventDispatcherOnDamaged`. |
| Call dispatcher (DSL) | WORKS | `(Default|CallOnDamaged :Amount 5.0 :DamageCauser self :DamageTag "(TagName=\"Data.Damage\")")` |
| Bind with matching custom event (DSL) — best | WORKS | `(Default|AssignOnPinged :self other)` — the DSL auto-creates AND wires a matching custom event `OnPinged_Event (Value)`; then write its body with `(event Custom|OnPinged_Event (Value) ...)`. Works for another actor's dispatcher (`:self` = the other actor ref, type ids `Default|...OnPinged` are listed for other BP classes too). |
| Bind/Unbind to an existing event/function | WORKAROUND | DSL cannot wire delegate pins: `(Default|BindEventtoOnDamaged (AddEvent|Custom|OnDamaged_0))` creates NEW empty custom events and leaves the pin unconnected; `(bind d (EventDispatchers|CreateEvent ...))` -> `(bind d ...) expression produced no output pin`; `:Delegate (EventDispatchers|CreateEvent :self self)` -> compile error `Event Dispatcher pin is not connected  Bind Event to On Damaged`. Recipe: write chain with DSL (compile error is expected), then `create_node {"type_id":"EventDispatchers|CreateEvent"}` -> `connect_pins` (CreateEvent out index 0 -> Bind/Unbind input `Delegate` (index 2)) -> `list_compatible_event_functions {"node":CE}` (errors `Connect the OutputDelegate pin to a delegate input pin first.` if not wired) -> `set_create_event_function {"node":CE,"function_name":"OnDamaged_0"}` -> `compile_blueprint`. Functions with a matching signature are bindable too. |
| Unbind all | WORKS | `(Default|UnbindallEventsfromOnDamaged)` / with `:self other` |
| Custom event WITH params, any name, any type (incl. class refs) | WORKAROUND (UI paste, verified) | Paste T3D (recipe A, section 5) — creates `OnHitReceived (Damage: double, Instigator: Actor, HitTag: GameplayTag, SpawnClass: Actor Class Reference)`:<br>`Begin Object Class=/Script/BlueprintGraph.K2Node_CustomEvent Name="K2Node_CustomEvent_706"`<br>`   CustomFunctionName="OnHitReceived"`<br>`   NodePosX=-300`<br>`   NodePosY=-400`<br>`   CustomProperties UserDefinedPin (PinName="Damage",PinType=(PinCategory="real",PinSubCategory="double"),DesiredPinDirection=EGPD_Output)`<br>`   CustomProperties UserDefinedPin (PinName="Instigator",PinType=(PinCategory="object",PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.Actor'"),DesiredPinDirection=EGPD_Output)`<br>`   CustomProperties UserDefinedPin (PinName="HitTag",PinType=(PinCategory="struct",PinSubCategoryObject="/Script/CoreUObject.ScriptStruct'/Script/GameplayTags.GameplayTag'"),DesiredPinDirection=EGPD_Output)`<br>`   CustomProperties UserDefinedPin (PinName="SpawnClass",PinType=(PinCategory="class",PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.Actor'"),DesiredPinDirection=EGPD_Output)`<br>`End Object`<br>Then fill the body with DSL `(event Custom|OnHitReceived (Damage Instigator HitTag SpawnClass) ...)`. |
| Component-bound event | WORKS | `add_component_bound_event {"component":{"refPath":"/Game/_Scratch/BP_ProbeActor.BP_ProbeActor_C:HitBox_GEN_VARIABLE"},"event_name":"OnComponentBeginOverlap","graph":EventGraph}` -> `K2Node_ComponentBoundEvent_0`. DSL head reads back as `(event OnComponentBeginOverlap(HitBox) (OverlappedComponent OtherActor OtherComp OtherBodyIndex bFromSweep SweepResult) ...)`. |

Dispatcher/DSL gotchas:
- `read_graph_dsl` is lossy for delegates: CreateEvent shows as `(EventDispatchers|CreateEvent _self)` without the bound function name; Assign shows `(Default|AssignOnDamaged (AddEvent|Custom|OnDamaged_Event))` which does NOT round-trip (re-writing it creates new empty events).
- **Stray events**: some `write_graph_dsl` calls on a BP that has dispatchers left unconnected custom events named `<Disp>_Event_0`, `<Disp>_Event_1` at about (-160,144) (not caused by find_node_types/get_node_type_pins — verified). After DSL writes, list entry nodes (`find_nodes(G,"",null,true)` + `get_node_infos`) and `delete_node` unconnected `*_Event_N` events.
- Rewriting an event chain with DSL replaced the old DSL-made nodes of that event, but a node created by `create_node` and linked to BeginPlay (`AssignDelegate`) stayed as an orphan. Always check `find_nodes` after rewrites.
- `read_graph_dsl` resolves member get/set of *another* BP ambiguously: `Class|BPProbeOther|SetHealth` read back as `Class|AbilitySystemTestAttributeSet|SetHealth` (first class with that member name). Never feed read output back blindly.

## 5. Graph readability (layout, comments, reroutes)

Raw facts (details + final recipe further below):
- DSL auto-placement: event at its existing position, then nodes every **280 px** to the right on the same row; branches/continuations
  start at +200 px y. It overlaps: e.g. `ForEachLoop` and `Delay` both at (1120,200), `SetHealth` and `PrintString` both at (1680,600);
  data nodes (MakeLiteral) are sometimes placed right of their consumer. => always arrange after writing.
- `arrange_nodes {"nodes":[...]}` WORKS: on a 16-node BeginPlay chain it produced columns x = 0/300/650/1000/1350/1700/2000/2350
  and separate rows per branch (no overlaps in coordinates). It also moved the event itself (BeginPlay 0,0 -> 0,1680), apparently to
  keep clear of other nodes already in the graph. Get the chain with `get_connected_subgraph {"node":<event>}` -> `[i["node"] for i in result]`.
- `set_node_position {"node":N,"pos":{"x":..,"y":..}}` WORKS for K2 nodes (read back via `get_node_infos[].position`).
- Reroute: `create_node {"graph":G,"type_id":"|AddRerouteNode...","pos":{"x":500,"y":1600}}` -> `K2Node_Knot_0` WORKS. Insert into a wire:
  `break_pins(out,in)`, `connect_pins(out, knot in idx0)`, `connect_pins(knot out idx0, in)`; the knot takes the wire type
  (`Array of BP Probe Other Object References`). `set_node_position` works on knots.
- Comment box: `create_node {"type_id":"|AddComment...", ...}` creates `EdGraphNode_Comment_0` in the graph but the tool then fails with
  `'EdGraphNode_Comment' object has no attribute 'set_node_pos'` (position not applied). Comment nodes are invisible to
  `find_nodes` (even with `node_class` `/Script/UnrealEd.EdGraphNode_Comment`), `get_node_infos` fails
  (`... has no attribute 'get_node_title'`), `set_node_position` fails (same set_node_pos error).
  ObjectTools on the comment ref (`.../EventGraph.EdGraphNode_Comment_0`): `list_properties` exposes only `commentColor`, `fontSize`,
  `bCommentBubbleVisible_InDetailsPanel`, `bColorCommentBubble`, `moveMode`, `nodeDetails`, `errorMsg`; `set_properties` of those
  WORKS (`{"commentColor":{"r":0.1,"g":0.4,"b":0.9,"a":1},"fontSize":24}` -> true). `NodeComment`, `NodeWidth`, `NodeHeight`,
  `NodePosX`, `NodePosY` -> `the following properties could not be set: ...`. => text/size/position not settable with tools.
- Node comment bubble on a regular node (`NodeComment`): not exposed by ObjectTools (`could not be read`), no DSL syntax.
- `delete_node` on a comment fails: `Cannot nativize 'EdGraphNode_Comment' as 'Object' (allowed Class type: 'K2Node')`.
  The BlueprintTools graph API only handles K2 nodes; comments must be handled through the editor UI (below).

### WORKING RECIPE A — comment boxes with exact text / color / size / position (clipboard paste)  [WORKAROUND, verified]

The Blueprint editor pastes Unreal T3D text from the Windows clipboard. Comment objects in T3D carry everything
(`NodeComment`, `NodeWidth`, `NodeHeight`, `CommentColor`, `FontSize`, `bCommentBubbleVisible`). Paste places the pasted set so that
its **average NodePos** lands on the paste location L (then snaps each node to the 16 px grid). A "counterweight" reroute node in
the same paste makes the average equal L, so every comment lands at its absolute `NodePosX/Y` (verified: comment at x=1312 exact,
the other at -32 instead of -48, i.e. within one 16 px grid cell).

1. Open the editor: EditorAppToolset `OpenEditorForAsset {"assetPath":"/Game/_Scratch/BP_ProbeDSL"}` (opens a separate window
   titled with the BP name). SlateInspector `Windows {"action":"list"}` -> `Windows {"action":"select","index":<i>}`.
2. SlateInspector `Snapshot {"ref":"","maxDepth":4}` to get the window ref, then `Snapshot {"ref":"<center splitter ref>","maxDepth":30}`
   (the splitter that contains tabs "Viewport"/"EventGraph"; was `sp9`). Click the graph tab (`tab "EventGraph"`), snapshot again.
   Graph nodes appear as `text "<node title>"` refs; the panel watermark appears as `text "BLUEPRINT"`.
   **Refs of graph nodes are renumbered after every change -> re-snapshot before each Click (a stale ref returns `false`).**
3. Focus the graph without selecting anything: `Click {"ref":"<text BLUEPRINT ref>"}`.
4. Calibrate L: PowerShell `Set-Clipboard` with
   ```
   Begin Object Class=/Script/BlueprintGraph.K2Node_Knot Name="K2Node_Knot_Cal"
      NodePosX=0
      NodePosY=0
   End Object
   ```
   then `PressKey {"key":"Ctrl+V"}`, read `get_node_infos` of `...EventGraph.K2Node_Knot_Cal` -> position = L; `delete_node` it.
   (L depends only on where you clicked and on pan/zoom; clicking the watermark again without panning gives the same L.
   Clicking a node title also works and is pan-independent: e.g. click "Event Tick" at node (0,416) -> L=(48,416).)
5. Build the paste text: N comment blocks at the wanted absolute positions T_i, plus one knot at `p_k = (N+1)*L - sum(T_i)`:
   ```
   Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="EdGraphNode_Comment_60"
      CommentColor=(R=0.100000,G=0.400000,B=0.900000,A=1.000000)
      FontSize=24
      bCommentBubbleVisible_InDetailsPanel=True
      bCommentBubbleVisible=True
      NodePosX=-48
      NodePosY=1600
      NodeWidth=2700
      NodeHeight=1350
      NodeComment="BeginPlay: find all BP_ProbeOther actors and ping them"
   End Object
   Begin Object Class=/Script/BlueprintGraph.K2Node_Knot Name="K2Node_Knot_93"
      NodePosX=<p_k.x>
      NodePosY=<p_k.y>
   End Object
   ```
   `Set-Clipboard -Value (Get-Content -Raw file.t3d)`; click the same anchor; `PressKey Ctrl+V`; `get_node_infos` on the knot (must equal
   p_k +-16) and `delete_node` it. Pasted objects keep their `Name` if free. Pins of pasted knots are created automatically.
6. Verify/read back: click watermark, `PressKey Ctrl+A`, `PressKey Ctrl+C`, PowerShell `Get-Clipboard -Raw` and regex the
   `EdGraphNode_Comment` blocks (NodePosX/Y, NodeWidth/Height, NodeComment). This is the only way to read comment geometry.
7. Screenshot check: click watermark, `PressKey Home` (= zoom to fit selection / graph), SlateInspector `Screenshot {"ref":""}`.
   Base64 PNG is 200-400 KB -> decode to a file, never inline.

Sizing: node sizes are not exposed; estimate the box from `get_node_infos` positions (+~300 px width, +~150-250 px height per node,
+60 px for the comment title bar, >=32 px margin because of grid snapping). Nested comments work (orange box inside the blue one).

Caution: `PressKey Delete` deletes the current selection. After a paste, the pasted objects stay selected. A `Click` on a comment
title that is covered by another comment's title bar did not change the selection -> the wrong comments were deleted.
Deleting a comment = select it alone (Click on its own title text inside the panel), then `PressKey Delete`; verify with Ctrl+A/C.

### WORKING RECIPE B — node comment bubbles (and any node-level field) via full-graph T3D round trip  [WORKAROUND, verified in EventGraph]

1. Calibrate L with the watermark anchor (recipe A step 4). 2. Click watermark, `Ctrl+A`, `Ctrl+C`, save `Get-Clipboard -Raw` to a file.
3. Edit the text: in the node's block insert before `NodeGuid=`: `bCommentBubblePinned=True`, `bCommentBubbleVisible=True`,
   `NodeComment="Wait 0.5s so spawned actors finish BeginPlay"`; optionally add comment blocks; append a counterweight knot with
   `p_k = (N+1)*L - sum(NodePos of all N top-level objects)` (objects without NodePosX/Y count as 0).
   Helper used: scratchpad `t3d_fix.py` (parse `Begin Object`/`NodePosX`/`NodePosY`, insert, append knot).
4. `Set-Clipboard`, click watermark, `Ctrl+A`, `Delete` (graph now empty: `find_nodes` -> `[]`), click watermark, `Ctrl+V`.
5. Result on BP_ProbeDSL: all 21 nodes came back with the **same names** (`K2Node_Event_0`, `K2Node_CallFunction_9`, ...), all links,
   positions snapped to 16 px (300->288, 650->640), bubble visible and pinned; `compile_blueprint {"warnings_as_errors":true}` ok;
   `read_graph_dsl` identical. Delete the counterweight knot afterwards.
Risks: function graphs (the FunctionEntry node cannot be deleted/duplicated -> links to it would be lost; use recipe A there),
timelines (pasting creates new timeline templates), anything referencing node names from outside the graph. Use only when needed.

### Other UI-only features seen in the node context menu (right-click on a selection, via SlateInspector)
`Click {"ref":"<node title text>","button":"right"}` opens a new window (`Windows list` shows an untitled window; `Snapshot` it).
Entries (UE 5.8, multi-selection): Delete, Cut, Copy, Duplicate, Refresh Nodes, Break Node Link(s), Goto Definition, Find References,
Rename, **Collapse Nodes, Collapse to Function, Collapse to Macro, Alignment >, Create Comment from Selection**, Disable/Enable Compile,
breakpoints. Close with `PressKey Escape`. Not exercised (collapse / align) — UI-only, no MCP tool.

(in progress)
