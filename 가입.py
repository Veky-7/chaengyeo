# -*- coding: utf-8 -*-
"""챙겨드림 서버 쪽 — 공단 회원가입을 폰 요청부터 끝까지 대신 한다 (Orca 내장 브라우저 조종).
폰이 보내는 것: {"type":"회원가입","시설":"수원도시공사","이름","생년월일"(YYMMDD),"성별"(여/남),"통신사"(SKT|KT|LG U+[ 알뜰폰]),"전화번호"}
단계마다 폰 화면에 「제가 보고 있는 화면」이 바뀐다. 사람이 채팅으로 주는 정보는 없다.

  python 가입.py 대기                 # 폰에서 회원가입 요청이 올 때까지 기다렸다가 → 본인인증 보안문자 화면까지 간다 (캡처 경로 출력)
  python 가입.py 보안문자 96580       # 보안문자 넣고 → 문자 요청 → 폰에 「숫자 읽어 주세요」 → 답 기다려 넣음 → 다음 화면 양식 덤프
  python 가입.py 상태 <상태> "<메모>"  # 손으로 폰 화면 바꿀 때

보안문자(그림 글자)만은 스크립트가 못 읽는다 — 서버 AI(클로드)가 캡처를 보고 `보안문자 NNNNN` 으로 이어 준다. 폰에는 「보안문자를 읽고 있어요」로 보인다.
"""
import sys, os, json, time, base64, subprocess, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util
_spec = importlib.util.spec_from_file_location("office", os.path.join(HERE, "_사무실.py")); office = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(office)
STATE = os.path.join(HERE, "_가입_상태.json")
EVID = os.path.normpath(os.path.join(HERE, "..", "..", "증거_실측"))

# ── Orca 브라우저 ─────────────────────────────────────────────
def orca(*args, retry=3):
    for i in range(retry):
        p = subprocess.run(["orca", *args, "--json"], capture_output=True, encoding="utf-8", errors="replace")
        try: d = json.loads(p.stdout)
        except Exception: d = {"ok": False, "error": {"message": p.stdout[:200] + p.stderr[:200]}}
        if d.get("ok"): return d.get("result", {})
        if "runtime_unavailable" in json.dumps(d) and i < retry - 1: time.sleep(2); continue
        raise RuntimeError(f"orca {' '.join(args)[:80]} → {d.get('error')}")
    return {}
def js(expr):
    r = orca("eval", "--expression", expr)
    return r.get("value", r.get("result", r)) if isinstance(r, dict) else r
def goto(url): orca("goto", "--url", url); wait_idle()
def wait_idle():
    try: orca("wait", "--load", "networkidle")
    except Exception: pass
def refs():
    r = orca("snapshot"); return r.get("refs", {}), r.get("origin", "")
def find(role=None, name=None, contains=None):
    rs, _ = refs()
    for k, v in sorted(rs.items(), key=lambda x: int(x[0][1:])):
        if role and v.get("role") != role: continue
        n = v.get("name", "")
        if name is not None and n != name: continue
        if contains is not None and contains not in n: continue
        return "@" + k
    return None
def wait_for(role=None, name=None, contains=None, sec=15):
    t = time.time()
    while time.time() - t < sec:
        r = find(role, name, contains)
        if r: return r
        time.sleep(1)
    raise RuntimeError(f"못 찾음: {role} {name or contains}")
def click(ref): orca("click", "--element", ref); time.sleep(1.2)
def press(role=None, name=None, contains=None, sec=15):
    """찾아서 누른다. 화면이 다시 그려져 ref 가 죽으면 다시 찾아 3번까지."""
    for i in range(3):
        try: click(wait_for(role, name, contains, sec)); return
        except RuntimeError as e:
            if "locate" not in str(e) or i == 2: raise
            time.sleep(1)
def fill(ref, val): orca("fill", "--element", ref, "--value", val); time.sleep(1.0)
def url():
    try: return orca("tab", "list")["tabs"]
    except Exception: return []
def cur_url():
    for t in url():
        if t.get("active"): return t.get("url", "")
    return ""
def shot(path):
    d = orca("screenshot"); open(path, "wb").write(base64.b64decode(d["data"])); return path

# ── 폰 화면 ───────────────────────────────────────────────────
def say(상태, 메모="", 결과="", 다음="", **extra):
    d = {"상태": 상태, "메모": 메모, "결과": 결과, "다음": 다음, "종류": "회원가입"}; d.update(extra)
    who = load_state().get("사람")
    if who: d.setdefault("받는사람", who)
    import requests
    requests.post(office.NT + office.T["RES"], data=json.dumps(d, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "text/plain"}, timeout=20)
    print(f"[폰] {상태} · {메모 or 결과}")
def ask_phone(항목, 결과, 제목="", 메모="", 초=240):
    """폰에 질문을 띄우고 말로 한 답을 기다린다."""
    say("질문", 메모, 결과, 항목=항목, 제목=제목, 시설="수원도시공사")
    t0 = time.time()
    while time.time() - t0 < 초:
        for d in office.받기("60s"):
            if d.get("type") in ("답", "인증번호") and (d.get("항목") == 항목 or (항목 == "인증번호" and d.get("type") == "인증번호")):
                if d.get("시각", "") >= time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t0 - 5)):
                    return d.get("값", "")
        time.sleep(3)
    return None
def load_state():
    try: return json.load(open(STATE, encoding="utf-8"))
    except Exception: return {}
def save_state(d): json.dump(d, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── 수원도시공사 통합회원가입 ────────────────────────────────
SUWON_START = "https://www.suwonudc.co.kr/PageLink.do?thirdMenuNo=&subMenuNo=100100&menuNo=100000&link=forward:use&tempParam1"
def suwon_to_captcha(p):
    """폰 요청 p → 약관 → KMC 본인인증(통신사·문자·이름·생년월일·전화) → 보안문자 캡처까지"""
    say("진행중", "수원도시공사 회원가입 화면을 열었어요")
    goto(SUWON_START)
    js("goSubMenuPage('100000','100300')"); wait_idle(); time.sleep(1)
    js("fnGoNext('N')"); wait_idle(); time.sleep(1)
    js("['rdoStplat11','rdoStplat21','chkAgradio1','chkAgradiob1'].forEach(function(id){var e=document.getElementById(id); if(e) e.checked=true;}); fnAgree(); 1"); wait_idle(); time.sleep(1)
    if "RlnmPinCnfirm" not in cur_url(): raise RuntimeError("약관 다음 화면이 아님: " + cur_url())
    say("진행중", "약관 4개를 읽고 동의했어요. 이제 휴대폰 본인 확인이에요")
    js("(function(){var f=document.reqKMCISForm; f.target=''; f.action='https://www.kmcert.com/kmcis/web/kmcisReq.jsp'; f.submit(); return 1})()")
    time.sleep(4); wait_idle()
    # 통신사
    carrier = p.get("통신사", "SKT")
    try: ref = wait_for("button", name=carrier, sec=20)
    except RuntimeError: ref = wait_for("button", contains=carrier.split()[0], sec=5)
    click(ref); say("진행중", f"통신사 {carrier} 골랐어요")
    click(wait_for("button", contains="문자(SMS) 인증"))
    chk = find("checkbox", contains="본인확인 이용 동의")
    if chk: orca("check", "--element", chk); time.sleep(0.8)
    press("button", name="다음")
    # 이름 → 생년월일/성별 → 전화
    fill(wait_for("textbox", name="이름"), p["이름"]); press("button", name="다음")
    say("진행중", f"이름 {p['이름']} 넣었어요")
    yy = p["생년월일"][:2]; y2000 = yy <= "26"
    gd = ("3" if p.get("성별") == "남" else "4") if y2000 else ("1" if p.get("성별") == "남" else "2")
    fill(wait_for("textbox", name="생년월일 6자리"), p["생년월일"])
    fill(wait_for("textbox", contains="주민등록번호 뒤 첫번째"), gd)
    say("진행중", "생년월일 넣었어요")
    fill(wait_for("textbox", name="휴대폰번호"), p["전화번호"])
    say("진행중", "전화번호 넣었어요. 보안문자를 읽고 있어요")
    wait_for("textbox", contains="보안문자")
    path = os.path.join(EVID, f"수원가입_보안문자_{time.strftime('%H%M%S')}.png")
    shot(path); return path

def suwon_after_captcha(code):
    fill(wait_for("textbox", contains="보안문자"), code)
    time.sleep(1)
    b = find("button", name="다음") or find("button", contains="확인") or find("button", contains="인증번호")
    if b: click(b)
    time.sleep(2)
    c = find("button", name="확인")   # 「입력정보 확인하기」 창
    if c and find("heading", contains="입력정보 확인"): click(c); time.sleep(2)
    return suwon_sms_wait()

def suwon_sms_wait():
    # 인증번호 칸이 떴는지
    box = None
    for _ in range(10):
        box = find("textbox", contains="인증번호")
        if box: break
        time.sleep(1)
    if not box:
        path = os.path.join(EVID, f"수원가입_보안문자후_{time.strftime('%H%M%S')}.png"); shot(path)
        raise RuntimeError("인증번호 칸이 안 보임 (보안문자 틀렸을 수 있음) → " + path)
    say("진행중", "문자를 보냈어요")
    code6 = ask_phone("인증번호", "본인 확인 문자가 왔어요. 말하기를 누르고, 문자에 있는 숫자 여섯 개를 읽어 주세요.", 메모="문자로 온 숫자를 기다려요")
    if not code6: raise RuntimeError("폰에서 인증번호가 안 왔음")
    say("진행중2", f"숫자 {' '.join(code6)} 받았어요. 확인 중이에요")
    fill(find("textbox", contains="인증번호"), code6)
    b = find("button", name="확인") or find("button", name="다음") or find("button", contains="확인")
    if b: click(b)
    time.sleep(4); wait_idle()
    path = os.path.join(EVID, f"수원가입_인증후_{time.strftime('%H%M%S')}.png"); shot(path)
    print("URL:", cur_url()); print("캡처:", path)
    # 다음 양식 덤프
    dump = js("(function(){var m=document.querySelector('#contents, .contents, main')||document.body; var f=Array.from(document.forms).map(function(f){return f.name+' -> '+f.action+' ['+Array.from(f.elements).filter(function(e){return e.name}).map(function(e){return e.type+':'+e.name+'='+(e.value||'')}).join(', ')+']'}).join('\\n'); return m.innerText.replace(/[ \\t]+\\n/g,'\\n').replace(/\\n{2,}/g,'\\n').slice(0,2500)+'\\n=====\\n'+f})()")
    print(dump)
    say("진행중2", "본인 확인 됐어요. 아이디를 만들고 있어요")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "대기":
        print("폰에서 회원가입 요청 기다리는 중…")
        p = office.기다리기("회원가입", int(a[1]) if len(a) > 1 else 600)
        if not p: print("요청 없음"); sys.exit(1)
        print("요청:", json.dumps({k: v for k, v in p.items() if k != "_시각"}, ensure_ascii=False))
        save_state(p)
        if p.get("시설") != "수원도시공사": print("아직 수원만 됨"); sys.exit(2)
        for k in ("이름", "생년월일", "전화번호"):
            if not p.get(k): say("확인필요", "", f"{k}이 안 왔어요. 앱에서 다시 말씀해 주세요"); sys.exit(3)
        path = suwon_to_captcha(p); print("보안문자 캡처:", path)
    elif a[0] == "보안문자":
        suwon_after_captcha(a[1])
    elif a[0] == "문자대기":
        suwon_sms_wait()
    elif a[0] == "상태":
        say(a[1], a[2] if len(a) > 2 else "", a[3] if len(a) > 3 else "")
