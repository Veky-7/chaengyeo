# -*- coding: utf-8 -*-
"""앱 올리기: index.html 의 판 번호(cbdr-version)를 지금 시각으로 바꾸고 → 커밋 → push.
  python 올리기.py "커밋 메시지"
🔴 index.html 을 고쳤으면 git 을 직접 치지 말고 이걸로 올린다 — 판 번호가 안 바뀌면 폰(홈 화면 앱)이 옛 판을 계속 쓴다 (9/15 사고).
"""
import sys, re, time, subprocess, os
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
msg = sys.argv[1] if len(sys.argv) > 1 else "앱 갱신"
p = "index.html"; s = open(p, encoding="utf-8").read()
ver = time.strftime("%Y%m%d%H%M")
s2, n = re.subn(r'(<meta name="cbdr-version" content=")\d+(">)', r'\g<1>' + ver + r'\g<2>', s)
if n != 1: print("판 번호 태그가 없다 — index.html <head> 에 <meta name=\"cbdr-version\" content=\"0\"> 필요"); sys.exit(1)
open(p, "w", encoding="utf-8").write(s2)
trail = "\n\nCo-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01ACwXBXyQ7aPxAeJ77ziKWP"
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-q", "-m", msg + f" (판 {ver})" + trail], check=True)
subprocess.run(["git", "push", "-q"], check=True)
print("올림 · 판", ver, "· 폰은 1~2분 뒤 스스로 새 판으로 바뀜")
