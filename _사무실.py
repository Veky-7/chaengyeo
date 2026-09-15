# -*- coding: utf-8 -*-
"""챙겨드림 어르신 화면 ↔ 사무실 중계 (ntfy).  python _사무실.py 받기 | 보내기 <상태> "<메모>" "<결과>"
상태: 요청 → 진행중(강좌 찾음) → 진행중2(신청서 씀) → 제출(자녀 확인) → 완료(결과 = 전화로 읽어줄 문장 · 다음 = 결과 화면 「다음」칸) | 확인필요
    python _사무실.py 벨 "김현순 님, 에코체육센터 실버반 당첨됐어요" "9/17~18 에코체육센터에 신분증 들고 가세요" --to 김현순   # 김현순 폰만 울림
🔴 폰이 여럿이면 --to <이름> 을 꼭 붙인다 (2026-09-15). 없으면 연결된 모든 폰에 간다.
    python _사무실.py 결과 "김현순 님, 에코체육센터 수영 실버반은 이번엔 안 됐어요. 다음 달에 다시 열리면 제가 먼저 알려드릴게요." --to 김현순
    → 벨 안 울림. 폰이 「수영장 추첨 결과 나왔어?」 에 이 문장을 바로 읽는다. 🔴 실제 마이페이지에서 읽은 것만 올린다. 리허설은 --to 테스트 로(김현순 폰에 안 남게)
회원가입(2026-09-15): 폰 「가입해 줘」 → {"type":"회원가입"} → 보내기 진행중(약관) → 보내기 인증번호 "" "문자로 온 숫자 여섯 개를 말해 주세요" → 폰이 {"type":"인증번호","값":"123456"}
    python _사무실.py 기다리기 인증번호 180        # 폰에서 숫자가 올 때까지 최대 180초 기다렸다가 값만 찍는다
    → 보내기 진행중2(아이디 만드는 중) → 보내기 완료 "" "회원이 됐어요" "이제 「신청해 줘」만 하시면 돼요"
"""
import sys, json, requests, io, os, time
sys.stdout.reconfigure(encoding="utf-8")
T=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"_topics.json"),encoding="utf-8")); NT="https://ntfy.sh/"
def 받기(since="all"):
    r=requests.get(NT+T["REQ"]+"/json",params={"poll":1,"since":since},timeout=20)
    out=[]
    for line in r.text.splitlines():
        if not line.strip(): continue
        m=json.loads(line)
        if m.get("event")!="message": continue
        try: d=json.loads(m["message"])
        except Exception: d={"원문":m["message"]}
        d["_시각"]=time.strftime("%m-%d %H:%M:%S",time.localtime(m["time"])); out.append(d)
    return out
받는사람=os.environ.get("CBDR_TO","")   # 비어 있으면 모든 폰. 사람별로 보내려면 CBDR_TO=김현순 또는 --to
def 보내기(상태, 메모="", 결과="", 다음="", 받는사람=None):
    d={"상태":상태,"메모":메모,"결과":결과,"다음":다음}
    if 받는사람 or globals()["받는사람"]: d["받는사람"]=받는사람 or globals()["받는사람"]
    r=requests.post(NT+T["RES"],data=json.dumps(d,ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"text/plain"},timeout=20)
    return r.status_code
def 벨(결과, 메모="", 받는사람=None):
    """진행 화면과 무관하게 전화 알림만 울린다 (목요일 추첨 결과 등). 받는사람을 주면 그 이름 폰만 울린다"""
    d={"type":"ring","결과":결과,"메모":메모}
    if 받는사람 or globals()["받는사람"]: d["받는사람"]=받는사람 or globals()["받는사람"]
    r=requests.post(NT+T["RES"],data=json.dumps(d,ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"text/plain"},timeout=20)
    return r.status_code
def 기다리기(종류="인증번호", 초=180):
    """폰에서 특정 type 메시지가 올 때까지 3초마다 폴링. 시작 이후 것만 본다."""
    시작=time.time()
    while time.time()-시작<초:
        for d in 받기("30s"):
            if d.get("type")==종류 and d.get("시각","")>=time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(시작-5)):
                return d
        time.sleep(3)
    return None
def 결과(문장, 받는사람=None):
    """추첨 결과 문장을 조용히 올려둔다(벨 없음). 폰은 「결과 나왔어?」에 이 문장을 읽는다. 목요일 결과알림.py 가 실제 마이페이지를 읽고 부른다."""
    d={"type":"결과","결과":문장}
    if 받는사람 or globals()["받는사람"]: d["받는사람"]=받는사람 or globals()["받는사람"]
    r=requests.post(NT+T["RES"],data=json.dumps(d,ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"text/plain"},timeout=20)
    return r.status_code
if __name__=="__main__":
    a=sys.argv[1:]
    if "--to" in a:   # python _사무실.py 벨 "..." "..." --to 김현순
        i=a.index("--to"); 받는사람=a[i+1]; a=a[:i]+a[i+2:]
    if not a or a[0]=="받기":
        for d in 받기(a[1] if len(a)>1 else "all"): print(d["_시각"], json.dumps({k:v for k,v in d.items() if k!="_시각"},ensure_ascii=False))
    elif a[0]=="보내기": print(보내기(a[1], a[2] if len(a)>2 else "", a[3] if len(a)>3 else "", a[4] if len(a)>4 else ""))
    elif a[0]=="벨": print(벨(a[1], a[2] if len(a)>2 else ""))
    elif a[0]=="결과": print(결과(a[1]))
    elif a[0]=="기다리기":
        d=기다리기(a[1] if len(a)>1 else "인증번호", int(a[2]) if len(a)>2 else 180)
        print(d.get("값","") if d else "없음"); sys.exit(0 if d else 1)
