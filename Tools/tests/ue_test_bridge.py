"""테스트 전용 에디터에서 로컬 Python 요청을 순차 실행한다.

요청·응답·준비 상태는 실행 중인 Unreal 프로젝트의 Saved에 둔다.
신뢰할 수 있는 로컬 테스트 파일만 전달하며 프로젝트 에셋을 저장하지 않는다.
"""
import json
import os
import time
import traceback
import unreal


unreal.EditorPythonScripting.set_keep_python_script_alive(True)

ROOT = os.path.abspath(unreal.Paths.project_saved_dir())
REQUEST = os.path.join(ROOT, "audit-request.json")
RESULT = os.path.join(ROOT, "audit-response.json")
ENV = {"unreal": unreal, "json": json, "os": os, "ROOT": ROOT}
LAST_ID = None
if os.path.isfile(REQUEST):
    try:
        with open(REQUEST, encoding="utf-8") as stream:
            LAST_ID = json.load(stream).get("id")
    except (OSError, ValueError):
        pass


def write_json(path, value):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=str)
    deadline = time.monotonic() + 1.0
    while True:
        try:
            os.replace(temporary, path)
            return
        except PermissionError as error:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("Saved 결과 파일 교체가 1초 동안 거부됐다: " + path) from error
            time.sleep(min(0.02, remaining))


def tick(delta):
    global LAST_ID
    if not os.path.isfile(REQUEST):
        return
    try:
        with open(REQUEST, encoding="utf-8") as stream:
            request = json.load(stream)
    except (OSError, ValueError):
        return
    if request["id"] == LAST_ID:
        return
    LAST_ID = request["id"]
    try:
        ENV["result"] = None
        exec(compile(request["code"], REQUEST, "exec"), ENV)
        response = {"id": LAST_ID, "ok": True, "result": ENV["result"]}
    except Exception:
        response = {"id": LAST_ID, "ok": False, "error": traceback.format_exc()}
    try:
        write_json(RESULT, response)
    except Exception:
        unreal.log_error("테스트 응답 기록 실패. Saved/audit-response.json과 로그를 확인한다.\n" + traceback.format_exc())


HANDLE = unreal.register_slate_post_tick_callback(tick)
write_json(os.path.join(ROOT, "audit-bridge-ready.json"), {"ready": True, "pid": os.getpid(), "saved_dir": ROOT})
unreal.log("SoulCombat 테스트 Python 브리지 준비 완료: " + ROOT)
