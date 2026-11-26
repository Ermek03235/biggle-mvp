"""Biggle desktop companion. Python 3.10+, standard library only."""
import json
import math
import os
import queue
import random
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
DEFAULT = dict(skin="Облачко", mood="Спокойный", task="", step="", note="")
PROFILE_ROOT = Path(os.getenv("LOCALAPPDATA") or Path.home())
PROFILE = PROFILE_ROOT / "Biggle" / "profile.json"
LEGACY_PROFILE = PROFILE_ROOT / "Beagle" / "profile.json"
if not PROFILE.exists() and LEGACY_PROFILE.is_file():
    PROFILE = LEGACY_PROFILE
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


def ghost(c, x, y, skin, phase, sprite, tea=False):
    c.create_image(x, y, image=sprite, tags="ghost")
    def poly(points, color):
        c.create_polygon(*[v + (x if i % 2 == 0 else y) for i, v in enumerate(points)],
                         fill=color, smooth=True, splinesteps=24, tags="ghost")
    def oval(a, b, d, e, color):
        c.create_oval(x+a, y+b, x+d, y+e, fill=color, outline="", tags="ghost")
    if skin == "Звездочёт":
        poly([-40,-40,-18,-47,-20,-80,9,-68,25,-48,34,-44,8,-36], SKINS[skin])
        oval(-16,-72,-9,-65,"#f7df99")
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


class Biggle:
    def __init__(self, root, path=PROFILE):
        self.root, self.path = root, path
        self.state = load(path)
        self.history, self.results = [], queue.Queue()
        self.busy = self.away = False
        self.anchor = None
        self.trip = None
        self.last_touch = self.last_activity = time.monotonic()
        self.touch_count = 0
        self.reaction = ""
        self.until = self.focus_end = 0
        art = Path(__file__).with_name("art")
        self.art = {name: tk.PhotoImage(master=root, file=str(art / (name + ".png")))
                    for name in ("room", "idle", "happy")}
        root.title("Biggle · Комната Бигги")
        root.configure(bg=PAPER)
        tk.Label(root,text="Biggle",font=("Georgia",24,"bold"),fg=INK,bg=PAPER).pack(anchor="w",padx=20,pady=(12,2))
        body = tk.Frame(root,bg=PAPER)
        body.pack(fill="both",expand=True,padx=16,pady=(4,16))
        left = tk.Frame(body,bg=PAPER)
        left.pack(side="left",fill="y",padx=(0,14))
        self.scene = tk.Canvas(left,width=430,height=430,highlightthickness=0)
        self.scene.pack()
        self.scene.create_image(0, 0, anchor="nw", image=self.art["room"])
        self.scene.tag_bind("ghost", "<Button-1>", lambda e: self.touch())
        ttk.Button(left,text="Выпустить Бигги на рабочий стол",command=self.fly).pack(fill="x",pady=10)
        ttk.Label(left,text="Касание — реакция Бигги  ·  Правая кнопка в полёте — домой").pack()
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
        self.model.insert(0,os.getenv("BIGGLE_MODEL") or os.getenv("BEAGLE_MODEL","qwen3:4b-instruct"))
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
        self.focus_btn = ttk.Button(task,text="Сосредоточиться на 25 минут",command=self.toggle_focus)
        self.focus_btn.pack(fill="x",pady=6)
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
        self.float = tk.Canvas(self.pet,width=214,height=220,bg=bg,highlightthickness=0,cursor="hand2")
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
            messagebox.showerror("Biggle",f"Не удалось сохранить профиль: {err}")
            return False
        self.state = state
        return True

    def remember(self):
        if self.persist({k:e.get().strip() for k,e in self.fields.items()}):
            self.status.configure(text="Запомнил. Можно закрыть Biggle и продолжить завтра.")

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

    def toggle_focus(self):
        if self.focus_end:
            self.focus_end = 0
            self.focus_btn.configure(text="Сосредоточиться на 25 минут")
        else:
            self.focus_end = time.monotonic() + 25 * 60
            self.focus_btn.configure(text="Отменить таймер")
            self.status.configure(text="Бигги напомнит о перерыве через 25 минут.")
    
    def respond(self, kind, words, now):
        self.reaction = kind
        self.words = words
        self.until = now + 3.3

    def touch(self):
        now = time.monotonic()
        self.touch_count = self.touch_count + 1 if now-self.last_touch < 2.0 else 1
        self.last_touch = self.last_activity = now
        mood = self.state["mood"]
        if self.touch_count >= 3:
            phrase = {"Деловой":"Минутку, я занят!", "Спокойный":"Эй, не надо трогать!", "Игривый":"Всё, щекотно! Улечу!"}[mood]
            self.respond("dodge", phrase, now)
            if self.away:
                self.start_trip(now, dodge=True)
        else:
            phrase = {"Деловой":"Рад тебя видеть.", "Спокойный":"Привет! Я рядом.", "Игривый":"Хи-хи, щекотно!"}[mood]
            self.respond("happy", phrase, now)

    def start_trip(self, now, dodge=False):
        x, y = self.pet.winfo_x(), self.pet.winfo_y()
        w = max(0, self.root.winfo_screenwidth()-214)
        h = max(0, self.root.winfo_screenheight()-220)
        dx = (1 if x < w/2 else -1) * 175 if dodge else random.choice((-1,1))*random.randint(60,190)
        dy = -52 if dodge else random.randint(-70,70)
        self.trip = (now, 0.65 if dodge else 3.2, x, y, max(0,min(w,x+dx)), max(0,min(h,y+dy)))

    def fly(self):
        now = time.monotonic()
        self.away = True
        self.last_activity = now
        self.next_flight = now + 1
        self.trip = self.anchor = None
        self.root.withdraw()
        self.pet.geometry(f"+{max(0,self.root.winfo_screenwidth()-230)}+150")
        self.pet.deiconify()
        self.pet.lift()
        self.respond("happy", "Полетаем?", now)

    def home(self):
        self.away = False
        self.trip = self.anchor = None
        self.last_activity = time.monotonic()
        self.pet.withdraw()
        self.root.deiconify()
        self.root.lift()

    def press(self,e):
        self.anchor = e.x_root,e.y_root,self.pet.winfo_x(),self.pet.winfo_y()
        self.trip = None
        self.last_activity = time.monotonic()
        self.moved = False

    def drag(self,e):
        if self.anchor is None:
            return
        ax,ay,x,y = self.anchor
        dx,dy = e.x_root-ax,e.y_root-ay
        if self.moved or abs(dx)+abs(dy)>5:
            self.moved = True
            x = max(0,min(x+dx,self.root.winfo_screenwidth()-214))
            y = max(0,min(y+dy,self.root.winfo_screenheight()-220))
            self.pet.geometry(f"+{x}+{y}")

    def release(self,e):
        if self.anchor is None:
            return
        self.anchor = None
        self.next_flight = time.monotonic() + 4
        if not self.moved:
            self.touch()

    def animate(self, now):
        if self.focus_end and now >= self.focus_end:
            self.toggle_focus()
            self.status.configure(text="25 минут прошли. Пора сделать паузу.")
            self.say("Бигги", "Пора сделать паузу. Запишем следующий шаг?")
            self.respond("happy", "Время передохнуть!", now)
        quiet_for = now - self.last_activity
        if self.away and self.anchor is None:
            if quiet_for >= 600 and not self.focus_end:
                self.home()
                self.respond("rest", "Я пока к себе, за чаем.", now)
            elif self.trip:
                start, duration, x, y, end_x, end_y = self.trip
                t = min(1, (now-start)/duration)
                ease = t*t*(3-2*t)
                self.pet.geometry(f"+{round(x+(end_x-x)*ease)}+{round(y+(end_y-y)*ease)}")
                if t >= 1:
                    self.trip = None
                    self.next_flight = now + random.uniform(3,7)
            elif now >= self.next_flight and quiet_for < 300 and not self.focus_end:
                self.start_trip(now)
        phase = now * 1.7
        target = self.float if self.away else self.scene
        target.delete("ghost")
        reacting = now < self.until
        happy = reacting and self.reaction == "happy"
        dodge = reacting and self.reaction == "dodge"
        x, y = (107,145) if self.away else (211,219)
        y += math.sin(phase)*(5 if self.away else 1.5)
        if happy:
            y -= abs(math.sin(phase*3))*6
        if dodge:
            x += math.sin(phase*5)*7
            if not self.away:
                y -= 15
        ghost(target,x,y,self.state["skin"],phase,self.art["happy" if happy else "idle"],tea=not self.away and not dodge)
        if reacting:
            label = target.create_text(x, y-83, text=self.words, font=("TkDefaultFont",10,"bold"),
                                       fill="#162e44", tags="ghost")
            l,t,r,b = target.bbox(label)
            backing = target.create_rectangle(l-5,t-4,r+5,b+4,fill="#e3faff",outline="#83bfd1",tags="ghost")
            target.tag_lower(backing,label)

    def tick(self):
        self.animate(time.monotonic())
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
    Biggle(root)
    root.mainloop()
