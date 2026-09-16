# -*- coding: utf-8 -*-
"""공지 자동 읽기 — 서버가 전주시설공단·수원도시공사 공지를 읽고, 새 글·바뀐 글은 AI가 어르신 말로 「구조」(누가·언제·어떻게)를 써서
폰 목록(목록.json)을 갱신한다. 오늘(9/15) 클로드가 손으로 한 일을 자동으로.

  python 공지읽기.py 한번            # 지금 읽어서 바뀐 것만 AI로 다시 쓰고 목록.json 갱신 → push
  python 공지읽기.py 강제            # 캐시 무시하고 전부 다시
  python 공지읽기.py 감시            # 1시간마다 「한번」 + 5초마다 폰 요청({type:"공지읽기"}) 받으면 그 자리에서 읽어 답
규칙(프로토타입 2_match.py 와 같다): 원문에 있는 것만 · 애매하면 「확정은 아니에요」 · 한 문장 25자 안쪽 · 전화번호.
AI = OpenAI(2_match.py 가 쓰던 키) · 공지 하나에 몇 원. 결과는 _공지_캐시.json 에 남긴다(원문 해시·AI 출력).
"""
import sys, os, re, json, time, hashlib, zipfile, io, subprocess, datetime as dt
if sys.stdout is None or sys.stderr is None:   # pythonw(창 없음)로 돌 때 — 로그 파일에 쓴다
    _lf = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_공지읽기_로그.txt"), "a", encoding="utf-8")
    sys.stdout = sys.stderr = _lf
else:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import requests
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_공지_캐시.json"); LIST = os.path.join(HERE, "목록.json")
import importlib.util
_s = importlib.util.spec_from_file_location("office", os.path.join(HERE, "_사무실.py")); office = importlib.util.module_from_spec(_s); _s.loader.exec_module(office)
UA = {"User-Agent": "Mozilla/5.0 (chaengyeo notice reader; contact haejajung7@gmail.com)"}
import urllib3; urllib3.disable_warnings()
RECENT_DAYS = 25   # 이보다 오래된 공지는 AI에 안 보낸다(비용·옛 정보)
def recent(date): 
    try: return (dt.date.today() - dt.date.fromisoformat(date.replace(".", "-"))).days <= RECENT_DAYS
    except Exception: return True
KEEP = re.compile(r"수영|강습|회원모집|신규반|아쿠아|생활체육")
SKIP = re.compile(r"결과|당첨|기존반|기존 강습반|재등록")   # 어르신 신규 신청과 무관

def hwpx_text(b):
    try:
        z = zipfile.ZipFile(io.BytesIO(b)); t = ""
        for n in z.namelist():
            if n.startswith("Contents/section"): t += re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "replace"))
        return re.sub(r"\s+", " ", t)
    except Exception: return ""
def clean(html):
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", html)
    t = re.sub(r"<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", t); t = re.sub(r"<[^>]+>", " ", t); t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()

# ── 수원도시공사 (광교웰빙 등)
def suwon():
    base = "https://www.suwonudc.co.kr"
    h = requests.get(base + "/main/cop/bbs/selectBoardList.do", params={"bbsId": "Notice_suwonsc3", "menuNo": "050000", "subMenuNo": "050400", "thirdMenuNo": "050401"}, headers=UA, timeout=30, verify=False).text
    out = []
    for m in re.finditer(r'<em[^>]*>([^<]*)</em>\s*<a[^>]*fn_inqire_notice\(\'(\d+)\',\'([^\']+)\'\)[^>]*>\s*([^<]+?)\s*</a>[\s\S]{0,400}?(\d{4}-\d{2}-\d{2})', h):
        cat, ntt, bbs, title, date = [x.strip() for x in m.groups()]
        if not KEEP.search(title) or SKIP.search(title): continue
        if not recent(date): continue
        d = requests.post(base + "/main/cop/bbs/selectBoardArticle.do", data={"nttId": ntt, "bbsId": bbs, "menuNo": "050000", "subMenuNo": "050400", "thirdMenuNo": "050401"}, headers=UA, timeout=30, verify=False).text
        body = clean(d); i = body.find(title); body = body[i:i + 4000] if i >= 0 else body[:4000]
        att = ""
        for fm in re.finditer(r"fn_downFile\('([^']+)','(\d+)'\)", d):
            fb = requests.get(base + f"/cmm/fms/FileDown.do?atchFileId={fm.group(1)}&fileSn={fm.group(2)}", headers=UA, timeout=60, verify=False).content
            att += hwpx_text(fb)[:3500]
        out.append({"공단": "수원도시공사", "지역": "수원", "분류": cat, "제목": title, "날짜": date, "url": base + f"/main/cop/bbs/selectBoardArticle.do?nttId={ntt}&bbsId={bbs}", "본문": body, "첨부": att})
    return out

# ── 전주시설공단 (에코·도내기샘·덕진·완산)
def jeonju():
    base = "https://www.jjss.or.kr"
    h = requests.get(base + "/index.9is", params={"contentUid": "ff8080816c5f9de6016cb2ba4741009c"}, headers=UA, timeout=30).text
    out = []
    for m in re.finditer(r'<span class="[^"]*">([^<]*)</span>\s*</td>\s*<td class="subject">\s*<a href="([^"]+)"[^>]*>\s*<span>([^<]+)</span>[\s\S]{0,300}?(\d{4}\.\d{2}\.\d{2})', h):
        cat, href, title, date = [x.strip() for x in m.groups()]
        if not KEEP.search(title) or SKIP.search(title): continue
        if not recent(date): continue
        url = base + "/planweb/board/" + href.lstrip("./").replace("&amp;", "&")
        d = requests.get(url, headers=UA, timeout=30).text
        body = clean(d); i = body.find(title); body = body[i:i + 1500] if i >= 0 else body[:1500]
        att = ""
        for fm in re.finditer(r'href="\./download\.9is\?([^"]+)"[^>]*>([^<]*)</a>', d):
            name = fm.group(2)
            if not re.search(r"안내문|안내|모집|요강|배정표", name): continue
            try:
                fb = requests.get(base + "/planweb/board/download.9is?" + fm.group(1).replace("&amp;", "&"), headers=UA, timeout=60).content
                if fb[:2] == b"PK": att += f"[{name}] " + hwpx_text(fb)[:3000] + " || "
            except Exception: pass
        out.append({"공단": "전주시설공단", "지역": "전주", "분류": cat, "제목": title, "날짜": date.replace(".", "-"), "url": url, "본문": body, "첨부": att})
    return out

# ── AI: 공지 → 카드(구조 = 어르신 말)
PROMPT = """당신은 70대 어르신을 돕는 상담원입니다. 아래는 공공 수영장 공지 원문(본문+첨부)입니다. 어르신이 「누가, 언제, 어떻게 신청하나」를 목소리로 듣고 바로 알 수 있게 카드로 정리하세요.

규칙 (어기면 안 됨):
1. 원문에 적힌 것만 쓴다. 날짜·시간·요금·방식을 추측하거나 지어내지 않는다. 없으면 빈칸.
2. 카드는 「수영 강습」과 「아쿠아로빅」만 만든다(있는 것만). 배드민턴·요가·필라테스 같은 다른 종목은 만들지 않는다. 시설 하나·종목 하나에 카드 하나.
3. 「구조」는 어르신께 스피커로 읽어드릴 말이다. 5~8문장, 한 문장 25자 안쪽, 반존대(~해요). 줄임말·기호 금지: 「9/17~23」이 아니라 「9월 17일부터 23일까지」처럼 전부 말로 쓴다.
   순서: ① 원래 다니던 분(기존회원)은 언제 → ② 처음 오는 분은 언제 → ③ 시민 우선이 있으면 누가 며칠 먼저 → ④ 인터넷인지 직접 가야 하는지 → ⑤ 뽑기(추첨)인지 먼저 온 순서인지 → ⑥ 뽑히면/붙으면 그다음 할 일(언제 어디 가서 뭘 들고) → ⑦ 휴장·수업 시작일 같은 주의 → ⑧ 마지막은 「제가 ~할게요」로 끝낸다(인터넷이면 「그날 제가 넣을게요」, 방문이면 「가입은 제가 미리 해 둘게요」).
4. 전문용어는 풀어 쓴다: 추첨 → 뽑기(추첨) · 선착순 → 먼저 온 순서 · 재등록 → 원래 다니던 분이 다시 등록 · 예비 → 대기 순서.
5. 「시작」「마감」은 처음 오는 분의 인터넷 접수 날짜(YYYY-MM-DD). 인터넷이 없으면 방문 날짜. 「방식」은 온라인/방문/둘다.
6. 「시간」은 어르신에게 맞는 반(실버·입문·기초·초급·아쿠아로빅)의 요일·시간만 짧게. 처음 배우는 사람용 반이 있으면 꼭 적는다.
7. 애매한 건 「구조」 끝에 「이건 확정은 아니에요, 제가 확인해 드릴게요」를 붙인다.
8. 원문에 없는 항목은 그냥 건너뛴다. 「~는 없어요」「~안 나왔어요」로 채우지 않는다. 원문이 링크·제목뿐이라 내용이 거의 없으면 카드를 만들지 말고 빈 배열 []로 답한다.
9. 날짜·시간은 숫자로 쓴다: 「9월 9일」「오후 2시」「저녁 7시」「새벽 6시」. 「구월 구일」처럼 한글 숫자로 쓰지 않는다.
11. 방문만 되는 날과 인터넷도 되는 날이 다르면 반드시 갈라 말한다: 「28일하고 29일은 직접 가야 하고, 30일은 인터넷도 돼요」처럼.
10. 뽑기(추첨)면 뽑는 날짜와 시간, 뽑힌 뒤 등록 기간(며칠 몇 시부터 며칠 몇 시까지)과 장소·준비물을 꼭 넣는다. 그게 어르신이 제일 놓치는 부분이다.

「구조」 본보기 (이 말투·길이로):
"광교는 세 갈래예요. 원래 다니던 분들이 9월 17일부터 23일까지 먼저 다시 등록하고요. 처음 오는 분은, 수원 사시면 9월 28일하고 29일에 직접 가서 접수하고, 인터넷으로는 9월 30일 새벽 6시부터 먼저 온 순서예요. 10월 1일부터 11일까지는 수영장을 고쳐서, 수업은 12일부터예요. 인터넷 접수는 그날 새벽에 제가 넣을게요."
"에코는 전달 15일하고 16일, 이틀만 인터넷으로 받아요. 먼저 온 순서가 아니라 17일 아침 10시에 뽑기예요. 뽑히면 문자가 오고, 그날 오후 2시부터 다음 날 저녁 7시까지 직접 가서 등록해야 해요. 안 뽑히면 문자가 안 와요. 그건 제가 확인해서 알려드려요."

공지 제목: {title} ({date}) · 공단: {org}
원문:
{body}

첨부 요강(있으면):
{att}

JSON 배열로만 답하세요:
[{{"시설": "", "종목": "수영 강습 또는 아쿠아로빅", "반": "", "방식": "온라인|방문|둘다", "시작": "YYYY-MM-DD", "마감": "YYYY-MM-DD",
  "시간": "", "대상": "", "비고": "", "전화": "", "구조": ""}}]"""
def llm_cards(n):
    spec = importlib.util.spec_from_file_location("cfg", r"D:\youtube\lifestyle-log\config.py"); cfg = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfg)
    from openai import OpenAI
    cli = OpenAI(api_key=cfg.OPENAI_API_KEY)
    res = cli.responses.create(model="gpt-5", input=PROMPT.format(title=n["제목"], date=n["날짜"], org=n["공단"], body=n["본문"][:3500], att=n["첨부"][:3500] or "(없음)"))
    txt = res.output_text.strip(); m = re.search(r"\[.*\]", txt, re.S)
    cards = json.loads(m.group(0)) if m else []
    for c in cards: c["지역"] = n["지역"]; c["출처"] = f"{n['제목']} ({n['날짜']})"; c["url"] = n["url"]
    return cards

def norm(s): return re.sub(r"\s|국민|체육|센터|수영장|종합운동장|스포츠", "", s or "")
def merge(cards_by_notice):
    """사람이 손본 카드(목록.json)를 뼈대로, 같은 시설 카드는 AI 것으로 「구조·비고·시작·마감·시간·대상·출처」를 갱신. 새 시설은 뒤에 붙인다."""
    cur = json.load(open(LIST, encoding="utf-8")) if os.path.exists(LIST) else []
    for c in cards_by_notice:
        bad = len(re.findall(r"없어요|안 나왔어요|안내 없어요", c.get("구조", ""))) >= 2 or not c.get("시작")
        if bad: print("  (원문 부족 → 기존 카드 유지)", c.get("시설"), c.get("종목")); continue
        def same(o):
            a, b = norm(o.get("시설")), norm(c.get("시설"))
            return bool(a and b) and (a in b or b in a) and (not c.get("종목") or o.get("종목") == c.get("종목"))
        hit = next((o for o in cur if same(o)), None)
        if hit:
            for k in ("구조", "비고", "시작", "마감", "시간", "대상", "출처", "url", "방식", "전화"):
                if c.get(k): hit[k] = c[k]
        else:
            if c.get("시설") and c.get("구조"): cur.append(c)
    json.dump(cur, open(LIST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return cur

def run(force=False):
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    notices = []
    for f in (suwon, jeonju):
        try: notices += f()
        except Exception as e: print("읽기 실패", f.__name__, e)
    print(f"공지 {len(notices)}건 (수영·강습 관련)")
    changed = []
    for n in notices:
        key = n["url"]; h = hashlib.md5((n["제목"] + n["본문"] + n["첨부"]).encode("utf-8")).hexdigest()
        if not force and cache.get(key, {}).get("hash") == h: continue
        print("→ AI로 다시 씀:", n["제목"][:50])
        try: cards = llm_cards(n)
        except Exception as e: print("  AI 실패", e); continue
        cache[key] = {"hash": h, "제목": n["제목"], "날짜": n["날짜"], "카드": cards, "시각": dt.datetime.now().isoformat(timespec="seconds")}
        changed += cards
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if changed:
        cur = merge(changed); print(f"목록 갱신 {len(changed)}장 → 카드 {len(cur)}장")
        try:
            subprocess.run(["git", "add", "목록.json"], cwd=HERE, check=True)
            subprocess.run(["git", "commit", "-q", "-m", f"목록.json: 공지 자동 읽기 {dt.datetime.now():%m-%d %H:%M} ({len(changed)}장)"], cwd=HERE, check=True)
            subprocess.run(["git", "push", "-q"], cwd=HERE, check=True); print("push 됨 — 폰은 다음 열 때 새 목록")
        except Exception as e: print("push 실패", e)
    else: print("바뀐 공지 없음")
    return changed

# ── 찾아드림: 오늘·내일 열리는 인터넷 접수를 그 지역 어르신 폰에 먼저 알린다 (기능 ① · 9/16 대표: "찾아서 알려주는 게 먼저다")
PEOPLE = {"전주": ["김현순"], "수원": ["정이서"]}          # 지역 → 폰 이름 (본선: 프로필 DB)
OFFERED = os.path.join(HERE, "_알림_기록.json")
def offer():
    cur = json.load(open(LIST, encoding="utf-8")) if os.path.exists(LIST) else []
    done = json.load(open(OFFERED, encoding="utf-8")) if os.path.exists(OFFERED) else {}
    today = dt.date.today(); n = 0
    for o in cur:
        if o.get("방식") not in ("온라인", "둘다") or not o.get("시작"): continue
        try: d0 = dt.date.fromisoformat(o["시작"]); d1 = dt.date.fromisoformat(o.get("마감") or o["시작"])
        except Exception: continue
        if d0 not in (today, today + dt.timedelta(days=1)): continue     # 오늘·내일 「새로 열리는」 것만 (이미 열려 있던 건 안 알림)
        key = f"{o['시설']}|{o.get('종목')}|{o['시작']}"
        if key in done: continue
        when = "내일" if d0 > today else ("오늘" if d0 == today else "지금")
        who = PEOPLE.get(o.get("지역"), [])
        msg = f"{o['시설']} {o.get('반') or o.get('종목','')} 접수가 {when} 열려요. 넣어드릴까요? 「넣어 줘」 하시면 제가 바로 넣을게요."
        for name in who:
            office.벨(msg, (o.get("구조") or "")[:120], 받는사람=name)
            import requests as _r
            _r.post(office.NT + office.T["RES"], data=json.dumps({"type": "제안", "받는사람": name, "카드": o, "결과": msg}, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "text/plain"}, timeout=20)
            print(f"[먼저 알림 → {name}] {msg}")
        done[key] = {"시각": dt.datetime.now().isoformat(timespec="seconds"), "받는사람": who}; n += 1
    json.dump(done, open(OFFERED, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not n: print("먼저 알릴 새 접수 없음")

if __name__ == "__main__":
    a = sys.argv[1:]; cmd = a[0] if a else "한번"
    if cmd in ("한번", "강제"): run(force=(cmd == "강제")); offer()
    elif cmd == "알림": offer()
    elif cmd == "감시":
        last = 0
        while True:
            if time.time() - last > 3600: run(); last = time.time()
            for d in office.받기("10s"):
                if d.get("type") == "공지읽기":
                    who = d.get("사람", ""); fac = d.get("시설", "")
                    cur = json.load(open(LIST, encoding="utf-8")) if os.path.exists(LIST) else []
                    hit = next((o for o in cur if fac and norm(fac) in norm(o.get("시설", ""))), None)
                    office.보내기("공지", "", (hit or {}).get("구조") or "그 공지는 아직 못 읽었어요. 확인하고 알려드릴게요.", 받는사람=who)
            time.sleep(5)
