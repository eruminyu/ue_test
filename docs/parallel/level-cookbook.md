# 레벨 제작 쿡북 (병렬 에디터 B)

UE 5.8.2 Unreal MCP로 L_CombatField, L_Dungeon_01의 지형과 조명을 만들며 확인한 레시피다. 표기: `SC` = `editor_toolset.toolsets.scene.SceneTools`, `AcT` = `editor_toolset.toolsets.actor.ActorTools`, `OT` = `editor_toolset.toolsets.object.ObjectTools`, `AT` = `editor_toolset.toolsets.asset.AssetTools`. OT의 `values`는 JSON **문자열**이다.

## 레벨 만들기와 불러오기

- `AT duplicate {"path":"/Engine/Maps/Templates/Template_Default","new_path":"/Game/SoulCombat/Maps/L_CombatField"}` → `AT save_assets {"asset_paths":["/Game/SoulCombat/Maps/L_CombatField"]}` → 현재 레벨 `AT is_dirty`가 false인지 확인 → `SC load_level {"level_path":"/Game/SoulCombat/Maps/L_CombatField"}` → `null`, 모달 없음. `SC get_current_level`로 확인한다.
- 복제한 Template_Default의 액터: `WorldSettings_1, Brush_1, DirectionalLight_0, SkyAtmosphere_0, SkyLight_0, ExponentialHeightFog_0, VolumetricCloud_0, PlayerStart_0, StaticMeshActor_0(라벨 SM_SkySphere), Floor_0(라벨 Floor, SM_Template_Map_Floor)` 외 시스템 액터. ref는 `/Game/SoulCombat/Maps/<맵>.<맵>:PersistentLevel.<이름>`.
- 템플릿 바닥 `Floor_0`: 위치 z -0.5, 스케일 8, 바운드 (-4000,-4000,-400.5)~(4000,4000,-0.5). **윗면이 피벗 높이**라서 z 0으로 옮기면 윗면이 z=0이 된다. 컴포넌트는 `Floor_0.StaticMeshComponent0`(Mobility Movable).
- 바닥 삭제: `SC remove_from_scene {"actor":{"refPath":"...PersistentLevel.Floor_0"}}`.

## 메시 피벗

- `editor_toolset.toolsets.static_mesh.StaticMeshTools get_bounds {"mesh":{"refPath":"/Game/LevelPrototyping/Meshes/SM_Cube.SM_Cube"}}` → (0,0,0)~(100,100,100). **SM_Cube 피벗은 최소 모서리다.** 박스 [x0,x1]×[y0,y1]×[z0,z1]은 `location (x0,y0,z0)`, `scale ((x1-x0)/100, (y1-y0)/100, (z1-z0)/100)`, 회전 0으로 놓는다. `AcT get_actor_bounds`가 정확히 그 값을 돌려준다.
- SM_Cylinder: (-50,-50,0)~(50,50,100), 피벗은 바닥 중심. 지름 120·높이 5 원판 = 스케일 (1.2,1.2,0.05), 위치 = (중심x, 중심y, 0).

## 액터 배치

- 스태틱 메시: `SC add_to_scene_from_asset {"asset_path":"/Game/LevelPrototyping/Meshes/SM_Cube","name":"GatePlatform","xform":{"location":{"x":-500,"y":1950,"z":0},"rotation":{"pitch":0,"yaw":0,"roll":0},"scale":{"x":10,"y":5,"z":0.2}}}` → `...PersistentLevel.StaticMeshActor_N`. `name`이 그대로 라벨이 된다(그래도 `AcT set_label`로 한 번 더 넣었다). 새 액터는 Mobility Static.
- 머티리얼: `OT set_properties {"instance":{"refPath":"...StaticMeshActor_N.StaticMeshComponent0"},"values":"{\"OverrideMaterials\":[\"/Game/SoulCombat/Materials/MI_SC_Wall.MI_SC_Wall\"]}"}` → true. 다시 읽으면 `[{"refPath":...}]`.
- 클래스 액터: `SC add_to_scene_from_class {"actor_type":{"refPath":"/Script/Engine.PlayerStart"},"name":"PlayerStart_GateReturn","xform":{...,"rotation":{"pitch":0,"yaw":-90,"roll":0}}}`. PlayerStart 태그는 `OT set_properties {"instance":<PlayerStart>,"values":"{\"PlayerStartTag\":\"GateReturn\"}"}`(기본값 `"None"`).
- 폴더: `SC set_actor_folder {"actor":<ref>,"folder_path":"Field/Sparring"}` → `null`. 확인은 `SC get_folders`, `SC get_actors_in_folder {"folder_path":...}`. 중간 폴더(`Field`, `Dungeon`)도 목록에 생긴다.
- 이동: `AcT set_actor_transform {"actor":<ref>,"xform":{"location":...,"rotation":...,"scale":...}}`. 스케일도 함께 넘긴다.

## 조명

- DirectionalLight: `...DirectionalLight_0.LightComponent0`의 `Intensity`(템플릿 6, Movable). 던전은 1.8(30%)로 낮췄다.
- 안개: `...ExponentialHeightFog_0.HeightFogComponent0`. 템플릿은 `FogInscatteringLuminance` (0,0,0), `SkyLightCaptureAffectsHeightFogStrength` 0이고 안개 색은 SkyAtmosphere에서 온다. 어둡게 하려면 `{"SkyAtmosphereAmbientContributionColorScale":{"r":0.55,"g":0.55,"b":0.65,"a":1}}`(기본 1,1,1). list_properties는 이름을 lowerCamel(`fogDensity`)로 보여 주지만 get/set은 UpperCamel(`FogDensity`)로 된다.
- PointLight: `SC add_to_scene_from_class {"actor_type":{"refPath":"/Script/Engine.PointLight"},...}` → 컴포넌트 `LightComponent0`. 기본값은 Intensity 8, IntensityUnits Candelas, AttenuationRadius 1000, **Mobility Stationary**. `{"Mobility":"Movable","Intensity":60,"AttenuationRadius":1800,"LightColor":{"r":1,"g":0.86,"b":0.7,"a":1}}`를 set_properties 한 번에 넣으면 true. LightColor는 8비트로 저장돼서 0.8588처럼 읽힌다.

## 대량 배치 (Python)

- ProgrammaticToolset `execute_tool_script`에는 스크립트를 JSON 파일(`{"script": "..."}`)로 넘긴다: `mcp_http.py --port 8001 call editor_toolset.toolsets.programmatic.ProgrammaticToolset execute_tool_script @args.json`. 인자 파일은 로컬 Python `json.dump({'script': open('x.py').read()}, open('args.json','w'))`로 만들면 따옴표 이스케이프를 신경 쓰지 않아도 된다.
- 박스 헬퍼(던전 바닥·벽 45개를 한 스크립트로):

  ```python
  def box(lbl,x0,x1,y0,y1,z0,z1,mat,fld):
      s=((x1-x0)/100.0,(y1-y0)/100.0,(z1-z0)/100.0)
      a=x("editor_toolset.toolsets.scene.SceneTools.add_to_scene_from_asset",
          {"asset_path":CUBE,"name":lbl,"xform":xf((x0,y0,z0),0,s)})
      setp(a["refPath"]+".StaticMeshComponent0",{"OverrideMaterials":[mat]})
      label(a,lbl); folder(a,fld)
  ```

- 틈 없는 던전 벽 규칙: 방 바닥 x[x0,x1] y[y0,y1] z[-20,0]. 북·남 벽은 x[x0-50,x1+50]로 모서리까지 덮고 서·동 벽은 y[y0,y1]. 문은 y[-300,300]을 비워 `_a`(y0~-300), `_b`(300~y1) 두 조각으로 만든다. 통로 바닥은 x[cx0,cx1] y[-300,300], 측벽은 방 벽 사이 x[cx0+50,cx1-50]의 y[300,350]/[-350,-300]. 이러면 통로 벽이 방 벽의 문 조각과 맞닿고 겹치지 않는다.
- 검증: 스크립트 하나로 모든 액터의 라벨·폴더·`get_actor_bounds`·OverrideMaterials를 읽어 `--out` 파일로 받고, 로컬 Python으로 10 cm 격자 래스터 검사를 했다(바닥 칸 옆이 빈 칸이면 새는 곳).

## 스크린샷 (탑다운)

- `EditorToolset.EditorAppToolset CaptureViewport` 인자 파일:
  `{"captureTransform":{"location":{"x":5100,"y":0,"z":6300},"rotation":{"pitch":-89.9,"yaw":-90,"roll":0},"scale":{"x":1,"y":1,"z":1}},"annotations":{"gridSpacing":1000,"gridExtent":11000,"gridHeight":1,"maxLabelDistance":0,"classFilter":null,"maxLabels":0},"bShowUI":false}`
  - FOV 90이라 가로 반폭 = 카메라 높이 z. 이미지는 2256×1077(약 2.1:1).
  - 피치는 정확히 -90 대신 -89.9. Yaw 0이면 화면 위 = +X, 오른쪽 = +Y. Yaw -90이면 오른쪽 = +X, 아래 = +Y라서 긴 던전을 가로로 담기 좋다.
  - `annotations`는 여섯 필드가 모두 필요하고 `classFilter: null`을 받는다. `maxLabelDistance 0`이면 라벨 없이 격자만 그린다.
- `mcp_http.py --port 8001 --out out.txt call ... @cap.json > /dev/null`로 받은 뒤 로컬에서 `base64.b64decode(json.load(f)['returnValue']['image']['data'])`를 PNG로 쓴다. 결과에 `cameraLocation`, `cameraRotation`, `cameraFOV`(90)도 들어 있다. 캡처는 맵을 dirty로 만들지 않았다.
