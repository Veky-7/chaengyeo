# -*- coding: utf-8 -*-
"""🔴 목요일 9/17 10:00 에코체육센터 실버반 추첨 결과 — 어머니(김현순) 전주공단 마이페이지를 화면 없이 읽어 폰에 올린다.
벨은 안 울린다(대표 9/15). 폰이 「신청한 거 나왔어?」 라고 물으면 올려둔 문장을 바로 읽는다.

  python 결과알림.py 상태                 # 지금 마이페이지 한 번 읽어서 찍는다 (로그인 검증)
  python 결과알림.py 감시 [09:58]          # 그 시각부터 60초마다 읽다가 「대기중」이 아니게 되면 결과 문장을 폰(김현순)에 올리고 끝
  python 결과알림.py 리허설 낙첨|당첨 --to 테스트   # 실제 안 읽고 문장만 올린다 (김현순 폰에 안 남게 이름을 「테스트」로)
계정 = _계정.json (계정저장.py 로 대표가 직접 넣음 · 깃 제외). 결과는 _결과.json 에도 남긴다.
"""
import sys, os, json, time, re, datetime as dt
if sys.stdout is not None: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
# 작업 스케줄러로 돌 때도 기록이 남게 — 화면 출력을 파일에도 쓴다
class _Tee:
    def __init__(self, path): self.f = open(path, "a", encoding="utf-8"); self.o = sys.stdout   # pythonw 면 None
    def write(self, x):
        if self.o is not None:
            try: self.o.write(x)
            except Exception: pass
        self.f.write(x); self.f.flush()
    def flush(self):
        if self.o is not None:
            try: self.o.flush()
            except Exception: pass
        self.f.flush()
    def reconfigure(self, **k): pass   # _사무실.py 가 sys.stdout.reconfigure 를 부른다
sys.stdout = _Tee(os.path.join(HERE, "_결과알림_로그.txt")); sys.stderr = sys.stdout
print("=== " + __import__("datetime").datetime.now().isoformat(timespec="seconds") + " 시작 " + " ".join(sys.argv[1:]))
import importlib.util
_s = importlib.util.spec_from_file_location("office", os.path.join(HERE, "_사무실.py")); office = importlib.util.module_from_spec(_s); _s.loader.exec_module(office)
ACC = os.path.join(HERE, "_계정.json"); OUT = os.path.join(HERE, "_결과.json")
LOGIN = "https://www.jjss.or.kr/index.9is?resultType=login"
MYPAGE = "https://www.jjss.or.kr/index.9is?contentUid=ff8080816f0de283016f11b8560e03f9"   # 마이페이지 > 강좌/강습 신청현황
WHO = "김현순"; ORG = "전주시설공단"
TARGET = ("에코체육센터", "실버반")

def sentence(status, row):
    """당첨상태 → 어르신 말. 원문 기준(공고 9/14: 결제 9/17 14:00~9/18 19:00 방문·신분증·당첨문자)"""
    st = (status or "").replace(" ", "")
    if "당첨" in st and "낙첨" not in st and "예비" not in st:
        return (f"{WHO} 님, 축하드려요. 에코체육센터 수영 실버반에 당첨됐어요. "
                f"이제 등록만 하시면 돼요. 오늘 오후 2시부터 내일 저녁 7시까지, 에코체육센터 안내실에 직접 가세요. "
                f"신분증하고 폰에 온 당첨 문자를 보여주시면 돼요. 돈은 노인 요금으로 오만사천 원이에요. "
                f"점심시간 12시부터 1시는 쉬어요. 내일 저녁 7시까지 안 가면 취소되니까, 내일 아침에 제가 한 번 더 알려드릴게요. "
                f"수업은 10월 1일부터 화요일·목요일·금요일 오후 2시예요.")
    if "예비" in st:
        n = re.sub(r"[^0-9]", "", st)
        return (f"{WHO} 님, 에코체육센터 실버반은 예비 {n + '번' if n else '후보'}이에요. "
                f"당첨된 분이 내일 저녁 7시까지 등록을 안 하면 차례가 넘어와요. 지금은 하실 게 없고, 차례가 오면 제가 바로 전화로 알려드릴게요.")
    if "낙첨" in st or "미당첨" in st or "탈락" in st:
        return (f"{WHO} 님, 에코체육센터 수영 실버반은 이번엔 뽑기에서 안 됐어요. 사람이 많아서 그래요, 잘못하신 게 아니에요. "
                f"다음 달 반 접수가 또 열려요. 보통 15일쯤이에요. 열리면 제가 먼저 알려드리고, 「넣어 줘」 한마디만 하시면 바로 넣을게요. "
                f"그동안 덕진 아쿠아로빅은 이미 접수돼 있으니까 그건 그대로 다니시면 돼요.")
    return None   # 대기중 등

def read_status(headless=True):
    from playwright.sync_api import sync_playwright
    acc = json.load(open(ACC, encoding="utf-8"))[ORG]
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=headless); pg = b.new_page()
        pg.goto(LOGIN, wait_until="domcontentloaded")
        pg.fill("#userId", acc["아이디"]); pg.fill("#userPassword", acc["비밀번호"])
        pg.keyboard.press("Enter"); pg.wait_for_load_state("networkidle")
        if "로그아웃" not in pg.content(): b.close(); raise RuntimeError("로그인 실패 (아이디/비밀번호 확인)")
        pg.goto(MYPAGE, wait_until="networkidle")
        rows = pg.evaluate("""() => Array.from(document.querySelectorAll('table tr')).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim().replace(/\\s+/g,' '))).filter(r => r.length > 8)""")
        b.close()
    for r in rows:
        line = " | ".join(r)
        if TARGET[0] in line and TARGET[1] in line:
            # 열: 번호 시설명 종목 강습타입 강습명 강습시간 강사 신청구분 사용기간 신청상태 당첨상태 결제상태 결제금액 재등록상태 신청일
            return {"행": r, "신청상태": r[9] if len(r) > 9 else "", "당첨상태": r[10] if len(r) > 10 else "", "결제상태": r[11] if len(r) > 11 else "", "시각": dt.datetime.now().isoformat(timespec="seconds")}
    return {"행": None, "당첨상태": "", "시각": dt.datetime.now().isoformat(timespec="seconds"), "표": rows}

def post_result(text, to=WHO):
    code = office.결과(text, 받는사람=to)
    json.dump({"문장": text, "받는사람": to, "시각": dt.datetime.now().isoformat(timespec="seconds")}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[폰·{to}] {code} · {text}")

if __name__ == "__main__":
    a = sys.argv[1:]; to = WHO
    if "--to" in a: i = a.index("--to"); to = a[i + 1]; a = a[:i] + a[i + 2:]
    cmd = a[0] if a else "상태"
    if cmd == "상태":
        r = read_status(); print(json.dumps(r, ensure_ascii=False, indent=1)); print("→ 문장:", sentence(r.get("당첨상태"), r))
    elif cmd == "감시":
        start = a[1] if len(a) > 1 else "09:58"
        hh, mm = map(int, start.split(":")); t0 = dt.datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
        if dt.datetime.now() < t0: print("대기 →", t0.strftime("%H:%M")); time.sleep((t0 - dt.datetime.now()).total_seconds())
        fails = 0
        while True:
            try:
                r = read_status(); st = r.get("당첨상태", ""); print(dt.datetime.now().strftime("%H:%M:%S"), "당첨상태 =", st or "(행 없음)"); fails = 0
                s = sentence(st, r)
                if s: post_result(s, to); break
            except Exception as e:
                fails += 1; print("읽기 실패", fails, e)
                if fails >= 10: print("10번 연속 실패 — 사람이 봐야 함"); break
            time.sleep(60)
    elif cmd == "리허설":
        kind = a[1] if len(a) > 1 else "낙첨"
        if to == WHO: print("🔴 리허설은 --to 테스트 로. 김현순 폰에 가짜 결과가 남는다"); sys.exit(2)
        post_result(sentence(kind, None).replace(WHO, to), to)
