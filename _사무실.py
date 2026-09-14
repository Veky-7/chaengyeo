# -*- coding: utf-8 -*-
"""챙겨드림 어르신 화면 ↔ 사무실 중계 (ntfy).  python _사무실.py 받기 | 보내기 <상태> "<메모>" "<결과>"
상태: 요청 → 진행중(공단 화면 열기) → 진행중2(강습 고르기) → 제출(신청 넣기) → 완료(결과 = 전화로 읽어줄 문장) | 확인필요"""
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
def 보내기(상태, 메모="", 결과=""):
    r=requests.post(NT+T["RES"],data=json.dumps({"상태":상태,"메모":메모,"결과":결과},ensure_ascii=False).encode("utf-8"),headers={"Content-Type":"text/plain"},timeout=20)
    return r.status_code
if __name__=="__main__":
    a=sys.argv[1:]
    if not a or a[0]=="받기":
        for d in 받기(a[1] if len(a)>1 else "all"): print(d["_시각"], json.dumps({k:v for k,v in d.items() if k!="_시각"},ensure_ascii=False))
    elif a[0]=="보내기": print(보내기(a[1], a[2] if len(a)>2 else "", a[3] if len(a)>3 else ""))
