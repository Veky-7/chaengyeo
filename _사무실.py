# -*- coding: utf-8 -*-
"""챙겨드림 어르신 화면 ↔ 사무실 중계 (ntfy).  python _사무실.py 받기 | 보내기 <상태> "<메모>" "<결과>"
상태: 요청 → 진행중(강좌 찾음) → 진행중2(신청서 씀) → 제출(자녀 확인) → 완료(결과 = 전화로 읽어줄 문장 · 다음 = 결과 화면 「다음」칸) | 확인필요
    python _사무실.py 벨 "김현순 님, 에코체육센터 실버반 당첨됐어요" "9/17~18 에코체육센터에 신분증 들고 가세요"   # 진행 화면 없이 전화만"""
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
def 보내기(상태, 메모="", 결과="", 다음=""):
    r=requests.post(NT+T["RES"],data=json.dumps({"상태":상태,"메모":메모,"결과":결과,"다음":다음},ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"text/plain"},timeout=20)
    return r.status_code
def 벨(결과, 메모=""):
    """진행 화면과 무관하게 전화 알림만 울린다 (목요일 추첨 결과 등)"""
    r=requests.post(NT+T["RES"],data=json.dumps({"type":"ring","결과":결과,"메모":메모},ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"text/plain"},timeout=20)
    return r.status_code
if __name__=="__main__":
    a=sys.argv[1:]
    if not a or a[0]=="받기":
        for d in 받기(a[1] if len(a)>1 else "all"): print(d["_시각"], json.dumps({k:v for k,v in d.items() if k!="_시각"},ensure_ascii=False))
    elif a[0]=="보내기": print(보내기(a[1], a[2] if len(a)>2 else "", a[3] if len(a)>3 else "", a[4] if len(a)>4 else ""))
    elif a[0]=="벨": print(벨(a[1], a[2] if len(a)>2 else ""))
