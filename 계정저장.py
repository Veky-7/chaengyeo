# -*- coding: utf-8 -*-
"""공단 계정을 노트북 파일(_계정.json · 깃 제외)에 저장하는 입력창. 채팅에 비밀번호를 치지 않기 위한 것.
  python 계정저장.py            # 창이 뜬다 → 공단·아이디·비밀번호 → 저장
저장 위치: 이 폴더/_계정.json  {"전주시설공단": {"아이디":..., "비밀번호":...}, ...}
읽는 쪽: 결과알림.py(목요일 10시 추첨 결과) · 가입.py/신청 스크립트
"""
import json, os, sys, tkinter as tk
from tkinter import ttk, messagebox
HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, "_계정.json")
def load():
    try: return json.load(open(F, encoding="utf-8"))
    except Exception: return {}
def save():
    org = cb.get().strip(); i = e_id.get().strip(); p = e_pw.get()
    if not (org and i and p): messagebox.showwarning("빠짐", "공단·아이디·비밀번호를 다 넣어 주세요"); return
    d = load(); d[org] = {"아이디": i, "비밀번호": p, "사람": e_who.get().strip()}
    json.dump(d, open(F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    messagebox.showinfo("저장됨", f"{org} 계정을 저장했어요.\n파일: {F}\n(비밀번호는 화면에 안 보여요)"); root.destroy()
root = tk.Tk(); root.title("챙겨드림 · 공단 계정 저장"); root.geometry("420x260"); root.attributes("-topmost", True)
frm = ttk.Frame(root, padding=16); frm.pack(fill="both", expand=True)
ttk.Label(frm, text="공단").grid(row=0, column=0, sticky="w", pady=4)
cb = ttk.Combobox(frm, values=["전주시설공단", "수원도시공사", "성남도시개발공사"], width=30); cb.grid(row=0, column=1, pady=4); cb.set("전주시설공단")
ttk.Label(frm, text="누구").grid(row=1, column=0, sticky="w", pady=4)
e_who = ttk.Entry(frm, width=32); e_who.grid(row=1, column=1, pady=4); e_who.insert(0, "김현순")
ttk.Label(frm, text="아이디").grid(row=2, column=0, sticky="w", pady=4)
e_id = ttk.Entry(frm, width=32); e_id.grid(row=2, column=1, pady=4)
ttk.Label(frm, text="비밀번호").grid(row=3, column=0, sticky="w", pady=4)
e_pw = ttk.Entry(frm, width=32, show="●"); e_pw.grid(row=3, column=1, pady=4)
ttk.Label(frm, text="이 노트북 파일에만 저장됩니다 · 깃·채팅·텔레그램에 안 감", foreground="#666").grid(row=4, column=0, columnspan=2, pady=(10, 4))
ttk.Button(frm, text="저장", command=save).grid(row=5, column=0, columnspan=2, pady=8)
e_id.focus(); root.bind("<Return>", lambda e: save()); root.mainloop()
