"""테스트 코드 파일을 프로젝트 Saved의 브리지로 전달하고 응답을 회수한다."""
import argparse
import json
import os
import time
import uuid
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("path", help="전달할 로컬 Python 테스트 파일")
parser.add_argument("--saved-dir", help="대상 에디터 프로젝트의 Saved. 기본값은 이 저장소 SoulCombat/Saved")
parser.add_argument("--out", help="Saved 안에 기록할 응답 파일 이름 또는 경로")
parser.add_argument("--timeout", type=float, default=15, help="브리지 응답 대기 시간(초). 테스트 완료 대기와 별개")
args = parser.parse_args()
root = os.path.abspath(args.saved_dir or Path(__file__).resolve().parents[2] / "SoulCombat" / "Saved")
if not os.path.isdir(root):
    raise SystemExit("대상 프로젝트 Saved가 없다: " + root)
if args.timeout <= 0:
    raise SystemExit("--timeout은 0보다 커야 한다.")

output = None
if args.out:
    output = os.path.abspath(os.path.join(root, args.out))
    try:
        inside_saved = os.path.normcase(os.path.commonpath([root, output])) == os.path.normcase(root)
    except ValueError:
        inside_saved = False
    if not inside_saved:
        raise SystemExit("--out 응답은 대상 프로젝트 Saved 안에 기록한다: " + output)

with open(args.path, encoding="utf-8-sig") as stream:
    request = {"id": str(uuid.uuid4()), "code": stream.read()}

temporary = os.path.join(root, "audit-request.tmp")
with open(temporary, "w", encoding="utf-8") as stream:
    json.dump(request, stream)
replace_deadline = time.monotonic() + 1.0
while True:
    try:
        os.replace(temporary, os.path.join(root, "audit-request.json"))
        break
    except PermissionError as error:
        remaining = replace_deadline - time.monotonic()
        if remaining <= 0:
            raise SystemExit("Saved 요청 파일 교체가 1초 동안 거부됐다. 요청 전달 실패: " + str(error))
        time.sleep(min(0.02, remaining))

deadline = time.monotonic() + args.timeout
while time.monotonic() < deadline:
    try:
        with open(os.path.join(root, "audit-response.json"), encoding="utf-8") as stream:
            response = json.load(stream)
    except (OSError, ValueError):
        time.sleep(0.1)
        continue
    if response.get("id") == request["id"]:
        rendered = json.dumps(response, ensure_ascii=False, indent=2)
        if output:
            with open(output, "w", encoding="utf-8") as stream:
                stream.write(rendered)
        print(rendered)
        raise SystemExit(0 if response["ok"] else 1)
    time.sleep(0.1)
raise SystemExit("검증 응답 시간 초과: 요청은 취소되지 않았다. 요청 ID " + request["id"]
                 + ", Saved/audit-response.json과 에디터 로그·PIE 상태를 먼저 확인한다.")
