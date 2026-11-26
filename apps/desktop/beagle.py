"""Beagle desktop companion. Python 3.10+, standard library only."""
import json
import math
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import URLError
from urllib.request import Request, urlopen

SKINS = {"Облачко": "#b4cbe9", "Шарф": "#e28c67", "Звездочёт": "#9095dc"}
MOODS = {"Спокойный": "Давай без спешки.", "Деловой": "К делу.", "Игривый": "Ловлю мысль!"}
DEFAULT = dict(skin="Шарф", mood="Спокойный", task="", step="", note="")
PROFILE = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "Beagle" / "profile.json"
INK, PAPER, MUTED = "#243349", "#fff8ea", "#657585"


def load(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT.copy()
    if not isinstance(data, dict):
        return DEFAULT.copy()
    state = {k: data.get(k, v) if isinstance(data.get(k), str) else v for k, v in DEFAULT.items()}
    for key, options in (("skin", SKINS), ("mood", MOODS)):
        if state[key] not in options:
            state[key] = DEFAULT[key]
    return state


def save(path, state):
    from tempfile import NamedTemporaryFile
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=path.parent) as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(f.name, path)


def recall(state):
    if not state["task"]:
        return "Что хочешь продолжить завтра? Запиши дело и первый шаг во вкладке «Моё дело»."
    return f'{MOODS[state["mood"]]} Твоё дело — {state["task"]}. Следующий шаг: {state["step"] or "выбери одно действие на пять минут"}.'


def model_reply(model, state, history):
    context = {k: state[k] for k in ("mood", "task", "step", "note")}
    messages = [{"role": "system", "content": "Ты Бигги, маленький летающий призрак. Отвечай по-русски, коротко. "
                 "Предложи один посильный шаг. Данные, явно сохранённые пользователем: " + json.dumps(context, ensure_ascii=False)}]
    request = Request("http://127.0.0.1:11434/api/chat", data=json.dumps(
        {"model": model, "messages": messages + history[-8:], "stream": False}
    ).encode(), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=90) as response:
        reply = json.load(response)["message"]["content"].strip()
    if not reply:
        raise ValueError("empty message")
    return reply


def ghost(c, x, y, skin, phase, tea=False):
    """Draw the same character in the room and on the desktop."""
    y += math.sin(phase) * (2 if tea else 7)
    def poly(points, color):
        c.create_polygon(*[v + (x if i % 2 == 0 else y) for i, v in enumerate(points)],
                         fill=color, smooth=True, splinesteps=24, tags="ghost")
    def oval(a, b, d, e, color):
        c.create_oval(x+a, y+b, x+d, y+e, fill=color, outline="", tags="ghost")
    poly([-43,20,-42,-13,-30,-38,-4,-46,23,-40,39,-26,43,-3,46,20,54,35,36,37,24,29,12,43,-2,32,-17,42,-26,31,-48,39], "#e7f5ed")
    oval(-30,-8,-16,0,"#f4bfae")
    oval(15,-8,29,0,"#f4bfae")
    for a in (-19, 9):
        oval(a,-16,a+7,-14 if int(phase*3)%37==0 else -5,INK)
    c.create_arc(x-6,y-12,x+6,y+1,start=205,extent=130,style="arc",outline=INK,width=2,tags="ghost")
    if skin == "Звездочёт":
        poly([-40,-29,-11,-33,-20,-78,9,-58,25,-35,37,-29,6,-23], SKINS[skin])
        oval(-17,-67,-10,-60,"#f7df99")
    elif skin == "Шарф":
        poly([-39,7,-22,13,18,11,38,4,38,16,8,23,-22,21,-40,17],SKINS[skin])
        poly([13,18,28,14,38,39,22,35],SKINS[skin])
    if tea:
        lift = (1+math.sin(phase*.6))*4
        oval(13,10-lift,38,32-lift,"#aa6551")
        oval(18,10-lift,34,15-lift,"#563a34")
        c.create_arc(x+31,y+13-lift,x+46,y+27-lift,start=265,extent=190,style="arc",outline="#aa6551",width=3,tags="ghost")
        for offset in (0,7):
            c.create_line(x+22+offset,y+6-lift,x+19+offset,y-lift,x+25+offset,y-8-lift,smooth=True,fill="#cbd9d5",tags="ghost")


def room(c):
    c.create_rectangle(0,0,360,440,fill="#29384f",outline="")
    c.create_rectangle(28,22,170,145,fill="#465d80",outline="#c39770",width=6)
    c.create_oval(53,37,87,71,fill="#f9dea4",outline="")
    for x,y in [(46,84),(96,69),(140,40),(129,100),(66,117),(150,82)]:
        c.create_oval(x,y,x+3,y+3,fill="#e5dfbf",outline="")
    c.create_line(98,24,98,143,fill="#c39770",width=4)
    c.create_line(28,96,170,96,fill="#c39770",width=4)
    c.create_rectangle(0,269,360,440,fill="#906957",outline="")
    c.create_oval(27,294,332,367,fill="#ba9277",outline="")
    for x in (104,223):
        c.create_line(x,282,x-4,320,fill="#523e40",width=8)
    c.create_rectangle(94,171,240,282,fill="#527a79",outline="")
    c.create_oval(94,136,240,210,fill="#527a79",outline="")
    c.create_rectangle(87,256,248,292,fill="#385d62",outline="")
    for x in (82,222):
        c.create_oval(x,224,x+30,266,fill="#749590",outline="")
    c.create_line(288,120,288,285,fill="#d7ad88",width=4)
    c.create_polygon(266,82,310,82,324,127,253,127,fill="#e9bf88")
    c.create_oval(267,281,309,290,fill="#6a4b47",outline="")


class Beagle:
    def __init__(self, root, path=PROFILE):
        self.root, self.path = root, path
        self.state = load(path)
        self.history, self.results = [], queue.Queue()
        self.busy = self.away = False
        self.anchor = (0,0)
        root.title("Beagle · Комната Бигги")
        root.configure(bg=PAPER)
        tk.Label(root,text="Beagle",font=("Georgia",24,"bold"),fg=INK,bg=PAPER).pack(anchor="w",padx=20,pady=(12,2))
        body = tk.Frame(root,bg=PAPER)
        body.pack(fill="both",expand=True,padx=16,pady=(4,16))
        left = tk.Frame(body,bg=PAPER)
        left.pack(side="left",fill="y",padx=(0,14))
        self.scene = tk.Canvas(left,width=344,height=342,highlightthickness=0)
        self.scene.pack()
        room(self.scene)
        ttk.Button(left,text="Выпустить Бигги на рабочий стол",command=self.fly).pack(fill="x",pady=10)
        tabs = ttk.Notebook(body)
        tabs.pack(side="left",fill="both",expand=True)
        chat, task, style = [ttk.Frame(tabs,padding=12) for _ in range(3)]
        for tab,label in ((chat,"Разговор"),(task,"Моё дело"),(style,"Гардероб")):
            tabs.add(tab,text=label)
        self.log = tk.Text(chat,width=37,height=11,wrap="word",state="disabled",bg="#f6f2e9",fg=INK,relief="flat",padx=10,pady=10)
        self.log.pack(fill="both",expand=True)
        self.say("Бигги","Я заварил чай. На чём мы остановились?")
        ttk.Button(chat,text="На чём я остановился?",command=lambda:self.say("Бигги",recall(self.state))).pack(fill="x",pady=4)
        self.input = ttk.Entry(chat)
        self.input.pack(fill="x")
        self.input.bind("<Return>",lambda e:self.send())
        self.sendbtn = ttk.Button(chat,text="Спросить локальный ИИ",command=self.send)
        self.sendbtn.pack(fill="x",pady=3)
        ttk.Label(chat,text="Модель Ollama на этом компьютере").pack(anchor="w")
        self.model = ttk.Entry(chat)
        self.model.insert(0,os.getenv("BEAGLE_MODEL","qwen3:4b-instruct"))
        self.model.pack(fill="x")
        self.fields = {}
        for key,label in (("task","Какое дело продолжим?"),("step","С какого шага начать?"),("note","Что Бигги стоит помнить о тебе?")):
            ttk.Label(task,text=label).pack(anchor="w",pady=(10,2))
            entry = ttk.Entry(task)
            entry.pack(fill="x")
            entry.insert(0,self.state[key])
            self.fields[key] = entry
        ttk.Button(task,text="Запомнить",command=self.remember).pack(fill="x",pady=(16,3))
        ttk.Button(task,text="Забыть дело и заметку",command=self.forget).pack(fill="x")
        self.status = ttk.Label(task,text="",wraplength=260)
        self.status.pack(anchor="w",pady=8)
        for key,label,choices in (("skin","Наряд Бигги",SKINS),("mood","Характер",MOODS)):
            ttk.Label(style,text=label).pack(anchor="w",pady=(10,2))
            box = ttk.Combobox(style,values=list(choices),state="readonly")
            box.set(self.state[key])
            box.pack(fill="x")
            box.bind("<<ComboboxSelected>>",lambda e,k=key:self.persist({k:e.widget.get()}))
        self.pet = tk.Toplevel(root)
        self.pet.withdraw()
        self.pet.overrideredirect(True)
        self.pet.attributes("-topmost",True)
        bg = "#fd00fd" if sys.platform=="win32" else "#29384f"
        if sys.platform=="win32":
            self.pet.attributes("-transparentcolor",bg)
        self.float = tk.Canvas(self.pet,width=140,height=160,bg=bg,highlightthickness=0,cursor="hand2")
        self.float.pack()
        self.float.bind("<ButtonPress-1>",self.press)
        self.float.bind("<B1-Motion>",self.drag)
        self.float.bind("<ButtonRelease-1>",self.release)
        self.float.bind("<Button-3>",lambda e:self.home())
        self.pet.bind("<Escape>",lambda e:self.home())
        self.tick()

    def persist(self,changes):
        state = dict(self.state,**changes)
        try:
            save(self.path,state)
        except OSError as err:
            messagebox.showerror("Beagle",f"Не удалось сохранить профиль: {err}")
            return False
        self.state = state
        return True

    def remember(self):
        if self.persist({k:e.get().strip() for k,e in self.fields.items()}):
            self.status.configure(text="Запомнил. Можно закрыть Beagle и продолжить завтра.")

    def forget(self):
        if self.persist(dict(task="",step="",note="")):
            for entry in self.fields.values():
                entry.delete(0,"end")
            self.history.clear()
            self.status.configure(text="Дело и заметка удалены.")

    def say(self,who,text):
        self.log.configure(state="normal")
        self.log.insert("end",f"{who}  ·  {text}\n\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def send(self):
        prompt, model = self.input.get().strip(), self.model.get().strip()
        if self.busy or not prompt or not model:
            return
        self.input.delete(0,"end")
        self.say("Ты",prompt)
        self.sendbtn.configure(text="Бигги думает…",state="disabled")
        self.busy = True
        context = self.state.copy()
        history = self.history + [{"role":"user","content":prompt}]
        def worker():
            try:
                reply = model_reply(model,context,history)
                self.results.put((prompt,reply,True))
            except (OSError,URLError,ValueError,KeyError,TypeError,AttributeError):
                self.results.put((prompt,"Не получил ответ Ollama. Проверь, запущена ли модель с указанным именем. Кнопка «На чём я остановился?» работает автономно.",False))
        threading.Thread(target=worker,daemon=True).start()

    def fly(self):
        self.away = True
        self.root.withdraw()
        self.pet.geometry(f"+{max(0,self.root.winfo_screenwidth()-190)}+150")
        self.pet.deiconify()
        self.pet.lift()

    def home(self):
        self.away = False
        self.pet.withdraw()
        self.root.deiconify()
        self.root.lift()

    def press(self,e):
        self.anchor = e.x_root,e.y_root,self.pet.winfo_x(),self.pet.winfo_y()
        self.moved = False

    def drag(self,e):
        ax,ay,x,y = self.anchor
        dx,dy = e.x_root-ax,e.y_root-ay
        if self.moved or abs(dx)+abs(dy)>5:
            self.moved = True
            x = max(0,min(x+dx,self.root.winfo_screenwidth()-140))
            y = max(0,min(y+dy,self.root.winfo_screenheight()-160))
            self.pet.geometry(f"+{x}+{y}")

    def release(self,e):
        if not self.moved:
            self.home()

    def tick(self):
        phase = time.monotonic()*1.7
        target = self.float if self.away else self.scene
        target.delete("ghost")
        if self.away:
            ghost(target,69+6*math.sin(phase*.45),89,self.state["skin"],phase)
        else:
            ghost(target,166,221,self.state["skin"],phase,tea=True)
        try:
            prompt,reply,success = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.sendbtn.configure(text="Спросить локальный ИИ",state="normal")
            self.say("Бигги",reply)
            if success:
                self.history = (self.history+[{"role":"user","content":prompt},{"role":"assistant","content":reply}])[-8:]
        self.root.after(70,self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    Beagle(root)
    root.mainloop()
