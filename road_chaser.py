"""
ROAD CHASER - ถนนนักซิ่ง
เกมแข่งรถแนว Road Fighter (Konami, 1984) เขียนด้วย Python + tkinter ไฟล์เดียว ไม่ต้องติดตั้ง library เพิ่ม
พัฒนาโดย Uncle Engineer

เป้าหมาย: ขับให้ถึงเส้นชัยก่อนน้ำมันหมด ชนขอบถนนหรือรถบรรทุก = ระเบิด
ชนรถคันอื่น = รถหมุน ต้องหักพวงมาลัยสวนเพื่อตั้งหลัก ชนรถสีรุ้งเพื่อเติมน้ำมัน

ปุ่มควบคุม:
    ← / →            : เลี้ยว
    ↑ / Z            : เร่ง (เกียร์ต่ำ สูงสุด 200 km/h)
    Shift / X        : เกียร์สูง (สูงสุด 400 km/h) - กดค้างพร้อมปุ่มเร่งเพื่อทำความเร็วสูงสุด
    ↓ / C            : เบรก
    P                : หยุดชั่วคราว
    M                : เปิด/ปิดเสียง
    Enter / Space    : เลือกเมนู
    Esc              : กลับหน้าแรก / ออกจากเกม
"""

import bisect
import json
import math
import os
import random
import sys
import tempfile
import time
import tkinter as tk
import wave
import webbrowser

try:
    import winsound
except ImportError:          # ไม่ใช่ Windows -> เล่นแบบไม่มีเสียง
    winsound = None

# ---------------- ค่าคงที่ ----------------
W, H = 600, 720
FIELD_L, FIELD_R = 60, 460
FIELD_W = FIELD_R - FIELD_L
FIELD_CX = (FIELD_L + FIELD_R) / 2
PY = 570                      # ตำแหน่งรถผู้เล่นบนจอ (แกน y)
PW, PH = 26, 46               # ขนาดรถผู้เล่น
K = 0.045                     # km/h -> พิกเซลต่อเฟรม (400 km/h = 18 px/frame)
FRAME_MS = 16
FUEL_MAX = 100
FUEL_BURN = FUEL_MAX / (62 * 60)   # น้ำมันเต็มถังวิ่งได้ ~62 วินาที
FUEL_CAR_BONUS = 20
MAX_CRASHES = 5               # ชนระเบิดได้กี่ครั้งต่อเกม ครบแล้ว Game Over
STAR_FRAMES = 420

FONT_TH = "Tahoma"
FONT_NUM = "Consolas"
FONT_TITLE = "Impact"

DEVELOPER = "Uncle Engineer"
PROJECT_URL = "https://github.com/UncleLabsBlacksmith/SimpleGame"
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "road_chaser_save.json")

# รหัสปุ่มบน Windows -> ชื่อปุ่ม (ให้เล่นได้แม้คีย์บอร์ดเป็นภาษาไทย)
VK = {90: "z", 88: "x", 67: "c", 80: "p", 77: "m"}

DIFFS = [
    {"name": "EASY", "th": "ง่าย", "fuel": 0.8, "density": 0.75, "espd": -10},
    {"name": "NORMAL", "th": "ปกติ", "fuel": 1.0, "density": 1.0, "espd": 0},
    {"name": "HARD", "th": "ยาก", "fuel": 1.2, "density": 1.3, "espd": 15},
]

STAGES = [
    {"name": "GRASSLAND", "th": "ทุ่งหญ้า", "length": 30000, "bg": "#4f9a2f", "road": "#6e6e6e",
     "edge": "#ffffff", "widths": (200, 220, 240), "median": 0.0, "curve": 0.5, "density": 0.9,
     "types": {"yellow": 6, "blue": 2, "purple": 0, "truck": 1}, "oil": 0.0, "rock": 0.0,
     "rival": False, "scenery": {"tree": 6, "flower": 3, "house": 1}},
    {"name": "WATER BRIDGES", "th": "สะพานข้ามน้ำ", "length": 34000, "bg": "#4f9a2f", "road": "#6e6e6e",
     "edge": "#ffffff", "widths": (170, 200, 240), "median": 0.25, "curve": 0.6, "density": 1.0,
     "types": {"yellow": 5, "blue": 3, "purple": 1, "truck": 1}, "oil": 0.04, "rock": 0.0,
     "rival": False, "water": True, "scenery": {"tree": 6, "flower": 2, "house": 1}},
    {"name": "SEASHORE", "th": "ริมทะเล", "length": 36000, "bg": "#e3cf8f", "road": "#707070",
     "edge": "#ffffff", "widths": (180, 220, 260), "median": 0.35, "curve": 0.7, "density": 1.05,
     "types": {"yellow": 4, "blue": 3, "purple": 2, "truck": 1}, "oil": 0.06, "rock": 0.0,
     "rival": True, "zone": "sea", "scenery": {"palm": 5, "house": 1, "bush": 2}},
    {"name": "MOUNTAIN", "th": "เทือกเขา", "length": 38000, "bg": "#8a7a63", "road": "#666666",
     "edge": "#ffffff", "widths": (150, 180, 220), "median": 0.15, "curve": 0.9, "density": 1.1,
     "types": {"yellow": 3, "blue": 3, "purple": 3, "truck": 2}, "oil": 0.04, "rock": 0.12,
     "rival": True, "zone": "cliff", "scenery": {"rock": 4, "pine": 4, "bush": 1}},
    {"name": "FOREST", "th": "ป่าลึก", "length": 40000, "bg": "#2f5f2a", "road": "#606060",
     "edge": "#ffffff", "widths": (150, 170, 200, 240), "median": 0.25, "curve": 0.9, "density": 1.2,
     "types": {"yellow": 3, "blue": 3, "purple": 3, "truck": 2}, "oil": 0.10, "rock": 0.03,
     "rival": True, "scenery": {"pine": 8, "tree": 3, "bush": 2}},
    {"name": "NIGHT HIGHWAY", "th": "ทางด่วนยามค่ำ", "length": 44000, "bg": "#151821", "road": "#3a3a44",
     "edge": "#ffd54f", "widths": (220, 260, 280), "median": 0.6, "curve": 0.6, "density": 1.4,
     "types": {"yellow": 3, "blue": 3, "purple": 4, "truck": 3}, "oil": 0.05, "rock": 0.0,
     "rival": True, "night": True, "scenery": {"building": 5, "bush": 1}},
]

VEHICLES = {
    "yellow": {"w": 26, "h": 44, "speed": (110, 160)},
    "blue": {"w": 26, "h": 44, "speed": (120, 165)},
    "purple": {"w": 26, "h": 44, "speed": (115, 155)},
    "truck": {"w": 30, "h": 88, "speed": (85, 115)},
    "fuel": {"w": 26, "h": 44, "speed": (130, 150)},
    "rival": {"w": 26, "h": 46, "speed": (0, 0)},
    "oil": {"w": 30, "h": 18, "speed": (0, 0)},
    "rock": {"w": 24, "h": 22, "speed": (0, 0)},
    "star": {"w": 24, "h": 24, "speed": (0, 0)},
}
TRAFFIC = ("yellow", "blue", "purple", "truck")
CAR_COLORS = {"yellow": "#f4c430", "blue": "#1e6be0", "purple": "#9b59b6", "rival": "#212121"}
TRUCK_COLORS = ["#2e7d32", "#1565c0", "#c62828", "#f57f17"]
RAINBOW = ["#ff1744", "#ff9100", "#ffea00", "#00e676", "#00b0ff", "#d500f9"]

MENU = ["start", "stage", "diff", "sound", "howto", "scores"]

# ---------------- เสียง (สร้างไฟล์ WAV เอง ไม่ต้องใช้ไฟล์ภายนอก) ----------------
SFX = {
    "select": [(988, .04, "sq")],
    "count": [(660, .12, "sq")],
    "go": [(1320, .3, "sq")],
    "bump": [(0, .08, "noise"), (110, .06, "sq")],
    "crash": [(0, .6, "noise")],
    "boom": [(0, .28, "noise")],
    "fuel": [(523, .05, "sq"), (659, .05, "sq"), (784, .05, "sq"), (1047, .1, "sq")],
    "star": [(784, .05, "sq"), (988, .05, "sq"), (1175, .05, "sq"), (1568, .14, "sq")],
    "low": [(330, .09, "sq"), (0, .05, "sq"), (330, .09, "sq")],
    "tick": [(1760, .025, "sq")],
    "clear": [(523, .12, "sq"), (659, .12, "sq"), (784, .12, "sq"), (1047, .35, "sq")],
}
SFX_PRIORITY = {"crash": 3, "clear": 3, "fuel": 2, "star": 2, "bump": 2, "go": 2, "boom": 2}


def write_wav(path, segments, rate=22050):
    data = bytearray()
    for freq, dur, kind in segments:
        n = int(rate * dur)
        for i in range(n):
            env = (1 - i / n) ** 1.3
            if kind == "noise":
                s = random.uniform(-1, 1)
            elif freq == 0:
                s = 0
            else:
                s = 1 if (i * freq / rate) % 1 < 0.5 else -1
            data.append(int(128 + s * 0.35 * env * 127))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)
        wf.setframerate(rate)
        wf.writeframes(bytes(data))


class Sound:
    def __init__(self, enabled):
        self.enabled = enabled
        self.files = {}
        self.busy_until = 0.0
        self.busy_prio = 0
        if winsound is None:
            return
        try:
            folder = os.path.join(tempfile.gettempdir(), "road_chaser_sfx_v1")
            os.makedirs(folder, exist_ok=True)
            for name, segs in SFX.items():
                path = os.path.join(folder, name + ".wav")
                if not os.path.exists(path):
                    write_wav(path, segs)
                self.files[name] = (path, sum(s[1] for s in segs))
        except OSError:
            self.files = {}

    def play(self, name):
        if not self.enabled or name not in self.files:
            return
        prio = SFX_PRIORITY.get(name, 1)
        now = time.monotonic()
        if now < self.busy_until and prio < self.busy_prio:
            return       # ไม่ให้เสียงเล็กๆ ตัดเสียงสำคัญ
        path, dur = self.files[name]
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            self.busy_until, self.busy_prio = now + dur, prio
        except RuntimeError:
            pass


# ---------------- ฟังก์ชันช่วยวาด ----------------
def R(x0, y0, x1, y1):
    return [x0, y0, x1, y0, x1, y1, x0, y1]


def shade(color, f):
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return "#%02x%02x%02x" % (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)))


def transform(pts, x, y, ang):
    if ang == 0:
        return [p + (x if i % 2 == 0 else y) for i, p in enumerate(pts)]
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    out = []
    for i in range(0, len(pts), 2):
        px, py = pts[i], pts[i + 1]
        out += [x + px * ca - py * sa, y + px * sa + py * ca]
    return out


SEDAN_BODY = [-10, -22, 10, -22, 13, -17, 13, 18, 10, 22, -10, 22, -13, 18, -13, -17]
RACER_BODY = [-9, -23, 9, -23, 12, -14, 13, 15, 10, 23, -10, 23, -13, 15, -12, -14]
GLASS, GLASS2, TIRE = "#9fd3ff", "#6fa8dc", "#111111"


def vehicle_parts(kind, color):
    """ชิ้นส่วนรถ (สี, จุด polygon) ในพิกัดท้องถิ่น หน้ารถหันขึ้นด้านบน"""
    if kind == "truck":
        parts = [(TIRE, R(x0, y0, x0 + 4, y0 + 10)) for x0 in (-17, 13) for y0 in (-36, 14, 28)]
        parts += [
            (color, [-12, -44, 12, -44, 14, -40, 14, -20, -14, -20, -14, -40]),
            (GLASS, R(-11, -38, 11, -31)),
            ("#d6d6d6", R(-15, -18, 15, 44)),
        ]
        parts += [("#9e9e9e", R(-14, yy, 14, yy + 1)) for yy in (-6, 6, 18, 30)]
        parts += [("#ff1744", R(-14, 41, -9, 44)), ("#ff1744", R(9, 41, 14, 44))]
        return parts
    racer = kind in ("player", "rival")
    body = RACER_BODY if racer else SEDAN_BODY
    wx = 16 if racer else 15
    parts = [(TIRE, R(sx, y0, sx + 5, y0 + 11)) for sx in (-wx, wx - 5) for y0 in (-17, 6)]
    parts.append((color, body))
    stripe = {"player": "#ffffff", "rival": "#ffd54f"}.get(kind)
    if stripe:
        parts.append((stripe, R(-3, -23, 3, 22)))
    parts += [
        (GLASS, [-9, -8, 9, -8, 7, -14, -7, -14]),
        (shade(color, 0.8) if not racer else color, R(-9, -7, 9, 8)),
        (GLASS2, [-8, 9, 8, 9, 9, 14, -9, 14]),
        ("#fff59d", R(-10, -21, -6, -19)), ("#fff59d", R(6, -21, 10, -19)),
        ("#ff1744", R(-10, 19, -6, 21)), ("#ff1744", R(6, 19, 10, 21)),
    ]
    if stripe:
        parts.append((stripe, R(-3, -7, 3, 8)))
        parts.append(("#222222", R(-14, 19, 14, 23)))          # สปอยเลอร์
    return parts


def star_points(r_out, r_in):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(-90 + i * 36)
        pts += [r * math.cos(a), r * math.sin(a)]
    return pts


STAR_PTS = star_points(13, 6)


class RoadChaser:
    def __init__(self, root):
        self.root = root
        root.title("ROAD CHASER - ถนนนักซิ่ง")
        root.resizable(False, False)
        self.cv = tk.Canvas(root, width=W, height=H, bg="#000000", highlightthickness=0)
        self.cv.pack()

        self.keys = set()
        root.bind("<KeyPress>", self.on_press)
        root.bind("<KeyRelease>", self.on_release)
        root.bind("<FocusOut>", self.on_focus_out)
        self.cv.bind("<Button-1>", self.on_click)
        self.cv.bind("<Motion>", self.on_motion)
        self.credit_box = None
        self.credit_hover = False

        self.save = self.load_save()
        self.sound = Sound(self.save["sound"])
        self.diff = self.save["diff"]
        self.sel_stage = self.save["unlocked"]
        self.menu_idx = 0
        self.frame = 0
        self.score = 0.0
        self.lives = MAX_CRASHES
        self.over_reason = ""
        self.state = "title"   # title, howto, scores, intro, play, pause, goal, over, ending
        self.setup_stage(self.sel_stage)
        self.loop()

    # ---------------- บันทึกข้อมูล ----------------
    def load_save(self):
        data = {"scores": [], "unlocked": 0, "best_time": {}, "sound": True, "diff": 1}
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, ValueError):
            pass
        if not isinstance(data["scores"], list):
            data["scores"] = []
        data["scores"] = [s for s in data["scores"] if isinstance(s, dict) and "score" in s][:5]
        if not isinstance(data["unlocked"], int) or not 0 <= data["unlocked"] < len(STAGES):
            data["unlocked"] = 0
        if not isinstance(data["best_time"], dict):
            data["best_time"] = {}
        if not isinstance(data["diff"], int) or not 0 <= data["diff"] < len(DIFFS):
            data["diff"] = 1
        data["sound"] = bool(data["sound"])
        return data

    def write_save(self):
        self.save["sound"] = self.sound.enabled
        self.save["diff"] = self.diff
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.save, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def top_score(self):
        return max([int(s["score"]) for s in self.save["scores"]] + [0])

    def record_score(self):
        score = int(self.score)
        if score <= 0:
            return None
        entry = {"score": score, "stage": self.stage + 1, "diff": DIFFS[self.diff]["name"]}
        scores = self.save["scores"] + [entry]
        scores.sort(key=lambda s: -int(s["score"]))
        self.save["scores"] = scores[:5]
        self.write_save()
        for i, s in enumerate(self.save["scores"]):
            if s is entry:
                return i + 1
        return None

    # ---------------- สร้างด่าน ----------------
    def setup_stage(self, i):
        st = STAGES[i]
        self.stage, self.st = i, st
        self.L = st["length"]
        rng = random.Random(7919 * (i + 1))    # ด่านเดิมได้ถนนหน้าตาเดิมทุกครั้ง

        kf = [(-3000, FIELD_CX, 210, 0), (1200, FIELD_CX, 210, 0)]
        y = 1200
        while True:
            y += rng.uniform(900, 1700)
            if y > self.L - 2200:
                break
            w = rng.choice(st["widths"])
            m = rng.choice((30, 50, 70)) if w >= 240 and rng.random() < st["median"] else 0
            maxoff = FIELD_W / 2 - w / 2 - 28
            c = FIELD_CX + rng.uniform(-1, 1) * maxoff * st["curve"]
            kf.append((y, c, w, m))
        kf.append((self.L - 700, FIELD_CX, 210, 0))
        kf.append((self.L + 8000, FIELD_CX, 210, 0))
        self.kf = kf
        self.kf_y = [k[0] for k in kf]

        self.water = []
        if st.get("water"):
            y = 2500
            while y < self.L - 2000:
                a = y
                b = min(y + rng.uniform(1500, 3200), self.L - 1200)
                self.water.append((a, b))
                y = b + rng.uniform(1500, 3000)

        scen = []
        y = -1500
        while y < self.L + 3000:
            y += rng.uniform(28, 64)
            l, r, _, _ = self.road_edges(y)
            side = rng.choice((-1, 1))
            lo, hi = (FIELD_L + 8, l - 20) if side < 0 else (r + 20, FIELD_R - 8)
            if hi - lo < 6:
                continue
            x = rng.uniform(lo, hi)
            kind = self.pick_scenery(rng, y, x, l, side)
            if kind:
                scen.append((y, x, kind))
        if st.get("night"):
            for y in range(-1200, self.L + 3000, 380):
                l, r, _, _ = self.road_edges(y)
                scen.append((y, l - 13, "lamp"))
                scen.append((y + 190, r + 13, "lamp"))
        scen.sort(key=lambda s: s[0])
        self.scen = scen
        self.scen_y = [s[0] for s in scen]

        # รีเซ็ตสถานะผู้เล่น
        self.d = 0.0
        self.px = FIELD_CX
        self.v = 0.0
        self.skid = 0.0
        self.angle = 0.0
        self.gear_hi = False
        self.fuel = float(FUEL_MAX)
        self.crash_t = 0
        self.invuln = 0
        self.star_t = 0
        self.go_t = 0
        self.shake = 0
        self.time = 0
        self.crashes = 0
        self.passed = 0
        self.tally_done = False
        self.tally_bonus = 0
        self.goal_t = 0
        self.new_best_time = False
        self.enemies = []
        self.particles = []
        self.texts = []
        self.next_spawn = 500.0
        self.next_fuel = 3500.0
        self.next_rival = 6000.0
        self.next_star = 9000.0

    def pick_scenery(self, rng, y, x, l, side):
        st = self.st
        if self.in_water(y):
            r = rng.random()
            return "wave" if r < 0.5 else "boat" if r < 0.54 else None
        if side < 0 and st.get("zone") == "sea" and x < self.shore_x(y, l):
            return "wave" if rng.random() < 0.6 else None
        if side < 0 and st.get("zone") == "cliff" and x < self.cliff_x(y, l):
            return "crag" if rng.random() < 0.5 else None
        names = list(st["scenery"])
        return rng.choices(names, weights=[st["scenery"][n] for n in names])[0]

    def in_water(self, wy):
        return any(a <= wy <= b for a, b in self.water)

    @staticmethod
    def shore_x(wy, l):
        return l - 55 - 14 * math.sin(wy / 90)

    @staticmethod
    def cliff_x(wy, l):
        return l - 38 - 8 * math.sin(wy / 60)

    def road_params(self, wy):
        kf = self.kf
        i = bisect.bisect_right(self.kf_y, wy) - 1
        i = max(0, min(len(kf) - 2, i))
        y0, c0, w0, m0 = kf[i]
        y1, c1, w1, m1 = kf[i + 1]
        t = max(0.0, min(1.0, (wy - y0) / (y1 - y0)))
        t = t * t * (3 - 2 * t)
        return c0 + (c1 - c0) * t, w0 + (w1 - w0) * t, m0 + (m1 - m0) * t

    def road_edges(self, wy):
        c, w, m = self.road_params(wy)
        return c - w / 2, c + w / 2, c - m / 2, c + m / 2

    def lane_x(self, wy, rel, hw):
        """แปลงตำแหน่งสัมพัทธ์ในเลน (-1..1) เป็นพิกัด x จริง รถจะวิ่งตามโค้งถนนเสมอ"""
        l, r, ml, mr = self.road_edges(wy)
        if mr - ml > 4:
            if rel < 0:
                lo, hi, t = l + hw + 3, ml - hw - 3, rel + 1
            else:
                lo, hi, t = mr + hw + 3, r - hw - 3, rel
        else:
            lo, hi, t = l + hw + 3, r - hw - 3, (rel + 1) / 2
        if hi < lo:
            return (lo + hi) / 2
        return lo + (hi - lo) * max(0.0, min(1.0, t))

    def rel_of(self, wy, x, hw):
        l, r, ml, mr = self.road_edges(wy)
        if mr - ml > 4:
            if x < (ml + mr) / 2:
                lo, hi = l + hw + 3, ml - hw - 3
                return max(-1.0, min(-0.02, (x - lo) / max(1, hi - lo) - 1))
            lo, hi = mr + hw + 3, r - hw - 3
            return max(0.0, min(1.0, (x - lo) / max(1, hi - lo)))
        lo, hi = l + hw + 3, r - hw - 3
        return max(-1.0, min(1.0, (x - lo) / max(1, hi - lo) * 2 - 1))

    def clamp_rel(self, e, val):
        l, r, ml, mr = self.road_edges(e["wy"])
        if mr - ml > 4:
            return max(-1.0, min(-0.02, val)) if e["rel"] < 0 else max(0.0, min(1.0, val))
        return max(-1.0, min(1.0, val))

    def sy(self, wy):
        return PY - (wy - self.d)

    # ---------------- เริ่มเกม ----------------
    def new_game(self):
        self.score = 0.0
        self.lives = MAX_CRASHES
        self.start_stage(self.sel_stage)

    def start_stage(self, i):
        self.setup_stage(i)
        self.state = "intro"
        self.intro_t = 220

    def respawn(self):
        l, r, ml, mr = self.road_edges(self.d)
        if mr - ml > 4:
            self.px = (l + ml) / 2 if self.px < (ml + mr) / 2 else (mr + r) / 2
        else:
            self.px = (l + r) / 2
        self.v = 0.0
        self.skid = 0.0
        self.angle = 0.0
        self.invuln = 120
        self.enemies = [e for e in self.enemies if abs(e["wy"] - self.d) > 230]

    # ---------------- อินพุต ----------------
    def keyname(self, e):
        if sys.platform.startswith("win") and e.keycode in VK:
            return VK[e.keycode]
        return e.keysym.lower()

    def on_press(self, e):
        k = self.keyname(e)
        self.keys.add(k)
        ok = k in ("return", "space", "z", "kp_enter")
        s = self.state
        if k == "m":
            self.sound.enabled = not self.sound.enabled
            self.write_save()
            return
        if k == "escape":
            if s == "title":
                self.root.destroy()
            else:
                self.to_title()
            return
        if s == "title":
            self.menu_key(k, ok)
        elif s in ("howto", "scores"):
            if ok:
                self.to_title()
        elif s == "play" and k == "p":
            self.state = "pause"
        elif s == "pause" and (k == "p" or ok):
            self.state = "play"
        elif s == "goal" and ok and self.tally_done:
            if self.stage + 1 < len(STAGES):
                self.start_stage(self.stage + 1)
            else:
                self.state = "ending"
                self.end_rank = self.record_score()
        elif s == "over" and ok:
            self.score = 0.0               # CONTINUE: เล่นด่านเดิมต่อ คะแนนและจำนวนชนเริ่มใหม่
            self.lives = MAX_CRASHES
            self.start_stage(self.stage)
        elif s == "ending" and ok:
            self.to_title()

    def menu_key(self, k, ok):
        item = MENU[self.menu_idx]
        if k == "up":
            self.menu_idx = (self.menu_idx - 1) % len(MENU)
            self.sound.play("select")
        elif k == "down":
            self.menu_idx = (self.menu_idx + 1) % len(MENU)
            self.sound.play("select")
        elif k in ("left", "right") or (ok and item in ("stage", "diff", "sound")):
            step = -1 if k == "left" else 1
            if item == "stage":
                self.sel_stage = (self.sel_stage + step) % (self.save["unlocked"] + 1)
                self.setup_stage(self.sel_stage)
            elif item == "diff":
                self.diff = (self.diff + step) % len(DIFFS)
            elif item == "sound":
                self.sound.enabled = not self.sound.enabled
            else:
                return
            self.write_save()
            self.sound.play("select")
        elif ok:
            if item == "start":
                self.new_game()
            elif item == "howto":
                self.state = "howto"
            elif item == "scores":
                self.state = "scores"

    def to_title(self):
        self.state = "title"
        self.sel_stage = min(self.sel_stage, self.save["unlocked"])
        self.setup_stage(self.sel_stage)

    def on_release(self, e):
        self.keys.discard(self.keyname(e))

    def on_focus_out(self, _e):
        self.keys.clear()
        if self.state == "play":
            self.state = "pause"

    def held(self, *names):
        return any(n in self.keys for n in names)

    def in_credit(self, x, y):
        b = self.credit_box
        return b is not None and b[0] <= x <= b[2] and b[1] <= y <= b[3]

    def on_motion(self, e):
        self.credit_hover = self.in_credit(e.x, e.y)
        self.cv.config(cursor="hand2" if self.credit_hover else "")

    def on_click(self, e):
        if self.in_credit(e.x, e.y):
            webbrowser.open(PROJECT_URL)

    # ---------------- ลูปหลัก ----------------
    def loop(self):
        self.frame += 1
        self.update()
        self.draw()
        if self.credit_box is None and self.credit_hover:
            self.credit_hover = False
            self.cv.config(cursor="")
        self.root.after(FRAME_MS, self.loop)

    def update(self):
        s = self.state
        if s in ("title", "howto", "scores"):
            self.d += 5
            if self.d > self.L - 1500:
                self.d = 0.0
        elif s == "intro":
            self.intro_t -= 1
            if self.intro_t in (180, 120, 60):
                self.sound.play("count")
            if self.intro_t <= 0:
                self.state = "play"
                self.go_t = 45
                self.sound.play("go")
        elif s == "play":
            self.update_play()
        elif s == "goal":
            self.update_goal()
        elif s in ("over", "ending"):
            self.update_effects()

    def update_play(self):
        self.time += 1
        self.fuel = max(0.0, self.fuel - FUEL_BURN * DIFFS[self.diff]["fuel"])
        if 0 < self.fuel < 15 and self.frame % 60 == 0:
            self.sound.play("low")
        if self.go_t > 0:
            self.go_t -= 1

        if self.crash_t > 0:
            self.crash_t -= 1
            if self.crash_t == 0:
                if self.lives <= 0:
                    self.game_over("crash")
                    return
                if self.fuel <= 0:
                    self.game_over()
                    return
                self.respawn()
            self.update_enemies()
            self.update_effects()
            return

        self.update_player()
        if self.crash_t == 0:
            self.d += self.v * K
            self.score += self.v / 45
            self.spawn()
            self.update_enemies()
            self.check_collisions()
        self.update_effects()

        if self.d >= self.L and self.crash_t == 0:
            self.reach_goal()
        elif self.fuel <= 0 and self.v <= 0 and self.crash_t == 0:
            self.game_over()

    def update_player(self):
        acc = self.held("z", "up")
        hi = self.held("x", "shift_l", "shift_r")
        brake = self.held("c", "down")
        self.gear_hi = hi
        if brake:
            self.v -= 6
        elif (acc or hi) and self.fuel > 0:
            top = 400 if hi else 200
            if self.v < top:
                a = (0.75 if self.v < 160 else 1.35) if hi else 2.3
                self.v = min(top, self.v + a)
            else:
                self.v = max(top, self.v - 1.6)
        else:
            self.v -= 1.0
        self.v = max(0.0, self.v)

        steer = 0.0
        if self.v > 0:
            sp = 2.4 + self.v / 400 * 1.8
            if self.held("left"):
                steer -= sp
            if self.held("right"):
                steer += sp

        if self.skid != 0:
            # รถหมุน: หักพวงมาลัยสวนทางเพื่อตั้งหลักได้เร็วขึ้น
            counter = steer != 0 and (steer > 0) != (self.skid > 0)
            self.px += self.skid
            self.skid *= 0.80 if counter else 0.955
            self.angle += self.skid * 7
            if abs(self.skid) < 0.35:
                self.skid = 0.0
        else:
            self.px += steer
            a = (self.angle + 180) % 360 - 180
            self.angle = 0.0 if abs(a) < 4 else a * 0.75

        if self.invuln > 0:
            self.invuln -= 1
        if self.star_t > 0:
            self.star_t -= 1
        if self.hits_wall():
            self.crash()

    def hits_wall(self):
        hw = PW / 2 - 3
        for dy in (PH / 2 - 6, -PH / 2 + 6):
            l, r, ml, mr = self.road_edges(self.d + dy)
            if self.px - hw < l or self.px + hw > r:
                return True
            if mr - ml > 4 and self.px + hw > ml and self.px - hw < mr:
                return True
        return False

    def crash(self):
        self.crash_t = 80
        self.v = 0.0
        self.skid = 0.0
        self.shake = 16
        self.crashes += 1
        self.lives = max(0, self.lives - 1)
        self.explode(self.px, self.d, 0.0, 55)
        self.sound.play("crash")
        if self.lives > 0:
            self.popup(self.px, self.d + 50, f"เหลือ {self.lives} ครั้ง", "#ff8a80")
        else:
            self.popup(self.px, self.d + 50, "ชนครบแล้ว!", "#ff5252")

    def explode(self, x, wy, vwy, n):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(1, 6)
            self.particles.append([x, wy, math.cos(a) * sp, vwy + math.sin(a) * sp, random.randint(20, 50),
                                   random.choice(["#ff5722", "#ffc107", "#ff9800", "#f44336", "#555555"])])

    def popup(self, x, wy, text, color):
        self.texts.append([x, self.sy(wy), text, color, 55])

    # ---------------- รถคันอื่น ----------------
    def add_enemy(self, kind, wy, rel=None):
        vt = VEHICLES[kind]
        lo, hi = vt["speed"]
        v = random.uniform(lo, hi) + DIFFS[self.diff]["espd"] if hi > 0 else 0.0
        l, r, ml, mr = self.road_edges(wy)
        if rel is None:
            rel = random.uniform(-0.9, 0.9)
            if mr - ml > 4 and abs(rel) < 0.05:
                rel = 0.3
        color = CAR_COLORS.get(kind, "#ffffff")
        if kind == "truck":
            color = random.choice(TRUCK_COLORS)
        e = {"kind": kind, "wy": wy, "rel": rel, "base": rel, "target": rel, "v": v,
             "vlat": 0.0, "spin": 0, "angle": 0.0, "hitcd": 0, "moved": False,
             "phase": random.uniform(0, math.tau), "life": 900, "dead": False,
             "w": vt["w"], "h": vt["h"], "color": color}
        self.enemies.append(e)
        return e

    def spawn(self):
        if self.d > self.L - 900:
            return
        top = self.d + PY + 120
        if self.d >= self.next_spawn:
            dens = self.st["density"] * DIFFS[self.diff]["density"]
            if any(abs(e["wy"] - top) < 150 for e in self.enemies if e["kind"] in TRAFFIC):
                self.next_spawn = self.d + 60
            else:
                types = self.st["types"]
                names = [n for n in types if types[n] > 0]
                kind = random.choices(names, weights=[types[n] for n in names])[0]
                self.add_enemy(kind, top)
                if random.random() < self.st["oil"]:
                    self.add_enemy("oil", top + random.uniform(160, 320))
                if random.random() < self.st["rock"]:
                    self.add_enemy("rock", top + random.uniform(160, 320))
                self.next_spawn = self.d + random.uniform(260, 520) / dens
        if self.d >= self.next_fuel:
            self.add_enemy("fuel", top + 60)
            self.next_fuel += random.uniform(5500, 8000)
        if self.d >= self.next_star:
            self.add_enemy("star", top + 200)
            self.next_star += random.uniform(11000, 16000)
        if self.st["rival"] and self.d >= self.next_rival:
            # คู่แข่งพุ่งมาจากด้านหลัง
            e = self.add_enemy("rival", self.d - (H - PY) - 60, rel=self.rel_of(self.d, self.px, 13))
            e["v"] = self.v + 40
            self.popup(self.px, self.d - 60, "RIVAL!", "#ffd54f")
            self.next_rival += random.uniform(9000, 13000)

    def update_enemies(self):
        top = self.d + PY + 500
        bottom = self.d - (H - PY) - 150
        keep = []
        for e in self.enemies:
            if e["dead"]:
                continue
            e["wy"] += e["v"] * K
            if e["hitcd"] > 0:
                e["hitcd"] -= 1
            if e["spin"] > 0:
                e["spin"] -= 1
                e["angle"] += 24
                old = e["rel"]
                e["rel"] += e["vlat"] / 60
                e["vlat"] *= 0.93
                l, r, ml, mr = self.road_edges(e["wy"])
                if abs(e["rel"]) > 1 or (mr - ml > 4 and (old < 0) != (e["rel"] < 0)):
                    self.destroy_enemy(e, bonus=300)     # ชนขอบถนนระเบิด
                    continue
                if e["spin"] == 0:
                    e["angle"] = 0.0
            else:
                self.enemy_ai(e)
            if e["wy"] < bottom:
                if e["kind"] in TRAFFIC:
                    self.passed += 1
                    self.score += 50
                continue
            if e["wy"] > top:
                continue
            keep.append(e)
        self.enemies = keep

    def move_rel(self, e, target, rate):
        target = self.clamp_rel(e, target)
        e["rel"] += max(-rate, min(rate, target - e["rel"]))

    def enemy_ai(self, e):
        k = e["kind"]
        dist = e["wy"] - self.d
        if k == "blue":
            # รถสีน้ำเงิน: เปลี่ยนเลนมาขวางเมื่อเราเข้าใกล้
            if not e["moved"] and 40 < dist < 320 and self.crash_t == 0:
                e["moved"] = True
                e["target"] = self.rel_of(e["wy"], self.px, 13)
            if e["moved"]:
                self.move_rel(e, e["target"], 0.03)
        elif k == "purple":
            # รถสีม่วง: ส่ายไปมาตลอด
            e["phase"] += 0.04
            self.move_rel(e, e["base"] + 0.55 * math.sin(e["phase"]), 0.05)
        elif k == "rival":
            e["life"] -= 1
            if e["life"] > 0 and self.crash_t == 0:
                if dist > 140:
                    e["v"] = max(60.0, self.v - 30)
                elif dist < -100:
                    e["v"] = self.v + 35
                else:
                    e["v"] = self.v + random.uniform(-8, 8)
                if abs(dist) < 150:
                    self.move_rel(e, self.rel_of(e["wy"], self.px, 13), 0.018)
            else:
                e["v"] = 460.0

    def destroy_enemy(self, e, bonus=0):
        e["dead"] = True
        ex = self.lane_x(e["wy"], e["rel"], e["w"] / 2)
        self.explode(ex, e["wy"], e["v"] * K, 30)
        self.sound.play("boom")
        if bonus:
            self.score += bonus
            self.popup(ex, e["wy"], f"+{bonus}", "#ffd54f")

    def check_collisions(self):
        pw, ph = PW / 2 - 2, PH / 2 - 3
        for e in self.enemies:
            if e["dead"] or e["hitcd"] > 0:
                continue
            ex = self.lane_x(e["wy"], e["rel"], e["w"] / 2)
            if abs(ex - self.px) < pw + e["w"] / 2 - 2 and abs(e["wy"] - self.d) < ph + e["h"] / 2 - 2:
                self.hit(e, ex)
                if self.crash_t > 0:
                    return

    def hit(self, e, ex):
        k = e["kind"]
        if k == "fuel":
            e["dead"] = True
            self.fuel = min(FUEL_MAX, self.fuel + FUEL_CAR_BONUS)
            self.score += 1000
            self.popup(ex, e["wy"], "FUEL +1000", "#69f0ae")
            self.sound.play("fuel")
        elif k == "star":
            e["dead"] = True
            self.star_t = STAR_FRAMES
            self.popup(ex, e["wy"], "STAR POWER!", "#ffea00")
            self.sound.play("star")
        elif self.star_t > 0:
            self.destroy_enemy(e, bonus=300)
        elif self.invuln > 0:
            return
        elif k in ("truck", "rock"):
            self.crash()
        elif k == "oil":
            e["hitcd"] = 90
            if self.skid == 0:
                self.skid = random.choice((-1, 1)) * 4.0
                self.popup(self.px, self.d + 30, "OIL!", "#bdbdbd")
                self.sound.play("bump")
        else:
            side = 1 if self.px >= ex else -1
            rear = abs(self.px - ex) < 12 and e["wy"] > self.d
            force = 3.2 + self.v / 160 + (1.5 if k == "rival" else 0)
            self.skid = side * force
            self.px += side * 3
            self.v *= 0.55 if rear else 0.82
            e["vlat"] = -side * (2.5 + self.v / 150)
            e["spin"] = 36
            e["hitcd"] = 25
            if rear:
                e["v"] += 30
            self.shake = 5
            self.sound.play("bump")

    def update_effects(self):
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[2] *= 0.94
            p[3] *= 0.94
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        for t in self.texts:
            t[1] -= 1.1
            t[4] -= 1
        self.texts = [t for t in self.texts if t[4] > 0]
        if self.shake > 0:
            self.shake -= 1

    # ---------------- เส้นชัย / จบเกม ----------------
    def reach_goal(self):
        self.state = "goal"
        self.goal_t = 0
        self.tally_done = False
        self.tally_bonus = 0
        self.skid = 0.0
        self.enemies = [e for e in self.enemies if e["wy"] < self.d - 120]
        key = str(self.stage)
        best = self.save["best_time"].get(key)
        self.new_best_time = best is None or self.time < best
        if self.new_best_time:
            self.save["best_time"][key] = self.time
        if self.stage + 1 < len(STAGES):
            self.save["unlocked"] = max(self.save["unlocked"], self.stage + 1)
        self.write_save()
        self.sound.play("clear")

    def update_goal(self):
        self.goal_t += 1
        self.v += (180 - self.v) * 0.05
        self.d += self.v * K
        l, r, _, _ = self.road_edges(self.d)
        self.px += ((l + r) / 2 - self.px) * 0.05
        a = (self.angle + 180) % 360 - 180
        self.angle = a * 0.8
        self.update_enemies()
        self.update_effects()
        if self.goal_t > 70 and not self.tally_done and self.goal_t % 2 == 0:
            if self.fuel >= 1:
                self.fuel -= 1
                self.score += 100
                self.tally_bonus += 100
                if self.goal_t % 6 == 0:
                    self.sound.play("tick")
            else:
                self.fuel = 0.0
                self.tally_done = True

    def game_over(self, reason="fuel"):
        self.state = "over"
        self.over_reason = reason
        self.over_rank = self.record_score()

    # ---------------- วาด ----------------
    def draw(self):
        c = self.cv
        c.delete("all")
        self.credit_box = None
        self.draw_world()
        s = self.state
        if s in ("intro", "play", "pause", "goal", "over"):
            self.draw_actors()
        if self.shake > 0:
            m = self.shake / 2
            c.move("all", random.uniform(-m, m), random.uniform(-m, m))
        self.draw_minimap()
        self.draw_hud()

        if s == "title":
            self.draw_title()
        elif s == "howto":
            self.draw_howto()
        elif s == "scores":
            self.draw_scores()
        elif s == "intro":
            self.draw_intro()
        elif s == "pause":
            self.banner("PAUSE", "หยุดชั่วคราว  -  กด P เพื่อเล่นต่อ", "#ffffff")
        elif s == "goal":
            self.draw_goal()
        elif s == "over":
            self.draw_over()
        elif s == "ending":
            self.draw_ending()
        elif s == "play":
            if self.go_t > 0:
                self.shadow_text(FIELD_CX, 300, "GO!", "#69f0ae", (FONT_TITLE, 60))
            if 0 < self.fuel < 15 and (self.frame // 15) % 2 == 0:
                self.shadow_text(FIELD_CX, 80, "FUEL LOW!", "#ff5252", (FONT_NUM, 22, "bold"))
            if self.star_t > 0:
                self.shadow_text(FIELD_CX, 115, f"STAR {self.star_t / 60:.1f}s", "#ffea00",
                                 (FONT_NUM, 14, "bold"))

    def shadow_text(self, x, y, text, color, font, anchor="center"):
        self.cv.create_text(x + 2, y + 2, text=text, fill="#000000", font=font, anchor=anchor)
        self.cv.create_text(x, y, text=text, fill=color, font=font, anchor=anchor)

    def draw_world(self):
        c = self.cv
        st = self.st
        d = self.d
        c.create_rectangle(FIELD_L, 0, FIELD_R, H, fill=st["bg"], outline="")

        samples = []
        for sy in range(-24, H + 25, 12):
            wy = d + PY - sy
            samples.append((sy, wy) + self.road_edges(wy))

        # พื้นที่ด้านซ้าย: ทะเล / หน้าผา
        zone = st.get("zone")
        if zone:
            fn = self.shore_x if zone == "sea" else self.cliff_x
            edge = [(max(FIELD_L, fn(wy, l)), sy) for sy, wy, l, r, ml, mr in samples]
            pts = []
            for x, sy in edge:
                pts += [x, sy]
            for x, sy in reversed(edge):
                pts += [FIELD_L, sy]
            c.create_polygon(pts, fill="#1e88e5" if zone == "sea" else "#5d4e42", outline="")
            line = []
            for x, sy in edge:
                line += [x, sy]
            c.create_line(line, fill="#e3f2fd" if zone == "sea" else "#3e342c", width=3)

        # แม่น้ำ (ด่านสะพาน)
        for a, b in self.water:
            top, bot = self.sy(b), self.sy(a)
            if bot >= 0 and top <= H:
                c.create_rectangle(FIELD_L, top, FIELD_R, bot, fill="#1976d2", outline="")
                c.create_rectangle(FIELD_L, top, FIELD_R, top + 6, fill="#c8b07a", outline="")
                c.create_rectangle(FIELD_L, bot - 6, FIELD_R, bot, fill="#c8b07a", outline="")

        # ทิวทัศน์ข้างทาง
        lo = bisect.bisect_left(self.scen_y, d - (H - PY) - 40)
        hi = bisect.bisect_right(self.scen_y, d + PY + 40)
        for wy, x, kind in self.scen[lo:hi]:
            self.draw_scenery(x, self.sy(wy), kind)

        # ถนน
        pts = []
        for sy, wy, l, r, ml, mr in samples:
            pts += [l, sy]
        for sy, wy, l, r, ml, mr in reversed(samples):
            pts += [r, sy]
        c.create_polygon(pts, fill=st["road"], outline="")

        # เกาะกลางถนน (เฉพาะช่วงที่ถนนแยก)
        run = []
        for smp in samples + [None]:
            if smp is not None and smp[5] - smp[4] > 2:
                run.append(smp)
                continue
            if len(run) > 1:
                mp = []
                for sy, wy, l, r, ml, mr in run:
                    mp += [ml, sy]
                for sy, wy, l, r, ml, mr in reversed(run):
                    mp += [mr, sy]
                c.create_polygon(mp, fill=shade(st["bg"], 0.85), outline=st["edge"], width=3)
            run = []

        # ราวสะพานช่วงที่อยู่เหนือน้ำ
        if self.water:
            run = []
            for smp in samples + [None]:
                if smp is not None and self.in_water(smp[1]):
                    run.append(smp)
                    continue
                if len(run) > 1:
                    for side in (2, 3):
                        off = -7 if side == 2 else 7
                        line = []
                        for smp2 in run:
                            line += [smp2[side] + off, smp2[0]]
                        c.create_line(line, fill="#37474f", width=8)
                        c.create_line(line, fill="#cfd8dc", width=4, dash=(10, 4))
                run = []

        left = []
        right = []
        for sy, wy, l, r, ml, mr in samples:
            left += [l, sy]
            right += [r, sy]
        c.create_line(left, fill=st["edge"], width=3)
        c.create_line(right, fill=st["edge"], width=3)

        # เส้นแบ่งเลนแบบประ
        start = int((d - (H - PY) - 100) // 90) * 90
        for wy in range(start, int(d + PY + 100), 90):
            a, b = self.lane_marks(wy), self.lane_marks(wy + 40)
            if len(a) != len(b):      # ช่วงที่จำนวนเลนเปลี่ยน ไม่ต้องวาด
                continue
            for xa, xb in zip(a, b):
                c.create_line(xa, self.sy(wy), xb, self.sy(wy + 40), fill=st["edge"], width=2)

        # เส้นสตาร์ท / เส้นชัย
        for wy, label in ((0, None), (self.L, "GOAL")):
            sy = self.sy(wy)
            if -40 < sy < H + 40:
                l, r, _, _ = self.road_edges(wy)
                n = int((r - l) // 10)
                sz = (r - l) / n
                for row in range(2):
                    for i in range(n):
                        col = "#ffffff" if (i + row) % 2 == 0 else "#111111"
                        c.create_rectangle(l + i * sz, sy - 10 + row * 10, l + (i + 1) * sz, sy + row * 10,
                                           fill=col, outline="")
                if label:
                    c.create_rectangle(l - 14, sy - 70, l - 8, sy + 10, fill="#9e9e9e", outline="")
                    c.create_rectangle(r + 8, sy - 70, r + 14, sy + 10, fill="#9e9e9e", outline="")
                    c.create_rectangle(l - 14, sy - 90, r + 14, sy - 62, fill="#c62828", outline="#ffffff",
                                       width=2)
                    c.create_text((l + r) / 2, sy - 76, text=label, fill="#ffffff", font=(FONT_NUM, 16, "bold"))

    def lane_marks(self, wy):
        l, r, ml, mr = self.road_edges(wy)
        if mr - ml > 4:
            return [(l + ml) / 2, (mr + r) / 2]
        c, w = (l + r) / 2, r - l
        if w >= 235:
            return [c - w / 4, c, c + w / 4]
        return [c]

    def draw_scenery(self, x, y, kind):
        c = self.cv
        if kind == "tree":
            c.create_oval(x - 14, y - 10, x + 16, y + 16, fill="#2c5e1a", outline="")
            c.create_oval(x - 15, y - 14, x + 13, y + 12, fill="#1b5e20", outline="#0d3310")
            c.create_oval(x - 9, y - 10, x + 3, y, fill="#43a047", outline="")
        elif kind == "pine":
            c.create_polygon(x, y - 20, x + 13, y + 10, x - 13, y + 10, fill="#1b4d1b", outline="#0b2b0b")
            c.create_polygon(x, y - 12, x + 9, y + 4, x - 9, y + 4, fill="#2e7d32", outline="")
            c.create_rectangle(x - 2, y + 10, x + 2, y + 15, fill="#5d4037", outline="")
        elif kind == "bush":
            c.create_oval(x - 9, y - 6, x + 9, y + 7, fill="#33691e", outline="#1b3d0d")
        elif kind == "flower":
            for dx, dy, col in ((-4, 0, "#ffeb3b"), (4, 2, "#ff80ab"), (0, -4, "#ffffff")):
                c.create_oval(x + dx - 2, y + dy - 2, x + dx + 2, y + dy + 2, fill=col, outline="")
        elif kind == "house":
            c.create_rectangle(x - 13, y - 9, x + 13, y + 12, fill="#efebe9", outline="#5d4037")
            c.create_polygon(x - 16, y - 8, x, y - 20, x + 16, y - 8, fill="#c62828", outline="#5d4037")
        elif kind == "palm":
            c.create_line(x, y + 14, x + 3, y - 6, fill="#795548", width=3)
            for ang in range(0, 360, 60):
                a = math.radians(ang)
                c.create_line(x + 3, y - 6, x + 3 + 14 * math.cos(a), y - 6 + 9 * math.sin(a),
                              fill="#2e7d32", width=3)
        elif kind == "rock":
            c.create_polygon(x - 12, y + 8, x - 8, y - 6, x + 3, y - 10, x + 12, y + 2, x + 8, y + 9,
                             fill="#9e9e9e", outline="#616161")
        elif kind == "crag":
            c.create_polygon(x - 10, y + 8, x - 4, y - 8, x + 9, y - 3, x + 11, y + 9,
                             fill="#4e4037", outline="#2f2620")
        elif kind == "wave":
            c.create_line(x - 8, y, x - 3, y - 3, x + 2, y, x + 7, y - 3, fill="#bbdefb", width=2)
        elif kind == "boat":
            c.create_polygon(x - 6, y - 12, x + 6, y - 12, x + 6, y + 8, x, y + 14, x - 6, y + 8,
                             fill="#ffffff", outline="#455a64")
        elif kind == "building":
            c.create_rectangle(x - 15, y - 18, x + 15, y + 18, fill="#263238", outline="#000000")
            for wx in (-9, 2):
                for wy2 in (-12, -2, 8):
                    lit = (int(x * 7 + wx + wy2 * 3 + y // 400) % 3) != 0
                    c.create_rectangle(x + wx, y + wy2, x + wx + 6, y + wy2 + 5,
                                       fill="#ffee58" if lit else "#37474f", outline="")
        elif kind == "lamp":
            c.create_oval(x - 16, y - 16, x + 16, y + 16, fill="#fff59d", stipple="gray25", outline="")
            c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#fffde7", outline="#9e9e9e")

    def draw_vehicle(self, x, y, kind, color, ang, shadow=True):
        c = self.cv
        parts = vehicle_parts(kind, color)
        if shadow:
            hw, hh = (15, 44) if kind == "truck" else (13, 22)
            c.create_polygon(transform(R(-hw, -hh, hw, hh), x + 4, y + 5, ang), fill="#000000",
                             stipple="gray50", outline="")
        for fill, pts in parts:
            c.create_polygon(transform(pts, x, y, ang), fill=fill, outline="#1a1a1a" if fill == color else "")

    def draw_actors(self):
        c = self.cv
        hazards, cars = [], []
        for e in self.enemies:
            if e["dead"]:
                continue
            (hazards if e["kind"] in ("oil", "rock", "star") else cars).append(e)

        for e in hazards:
            x = self.lane_x(e["wy"], e["rel"], e["w"] / 2)
            y = self.sy(e["wy"])
            if e["kind"] == "oil":
                c.create_oval(x - 16, y - 9, x + 16, y + 9, fill="#141414", outline="")
                c.create_oval(x - 8, y - 5, x + 2, y - 1, fill="#424242", outline="")
            elif e["kind"] == "rock":
                c.create_polygon(x - 12, y + 9, x - 9, y - 6, x + 2, y - 11, x + 12, y - 1, x + 9, y + 10,
                                 fill="#8d8d8d", outline="#424242", width=2)
            else:
                col = RAINBOW[(self.frame // 4) % len(RAINBOW)]
                c.create_polygon(transform(STAR_PTS, x, y, self.frame * 4), fill="#ffea00", outline=col, width=2)

        for e in cars:
            x = self.lane_x(e["wy"], e["rel"], e["w"] / 2)
            y = self.sy(e["wy"])
            if e["kind"] == "fuel":
                col = RAINBOW[(self.frame // 5) % len(RAINBOW)]
                self.draw_vehicle(x, y, "sedan", col, e["angle"])
                if e["angle"] == 0:
                    c.create_text(x, y, text="F", fill="#ffffff", font=(FONT_NUM, 10, "bold"))
            else:
                kind = "truck" if e["kind"] == "truck" else "rival" if e["kind"] == "rival" else "sedan"
                self.draw_vehicle(x, y, kind, e["color"], e["angle"])

        # รถผู้เล่น
        if self.crash_t == 0 and self.state != "over":
            if self.st.get("night"):
                c.create_polygon(self.px - 9, PY - 22, self.px + 9, PY - 22, self.px + 50, PY - 190,
                                 self.px - 50, PY - 190, fill="#fff59d", stipple="gray25", outline="")
            if self.invuln == 0 or (self.frame // 4) % 2 == 0:
                color = RAINBOW[(self.frame // 3) % len(RAINBOW)] if self.star_t > 0 else "#e53935"
                self.draw_vehicle(self.px, PY, "player", color, self.angle)
                if self.star_t > 0:
                    c.create_oval(self.px - 22, PY - 30, self.px + 22, PY + 30,
                                  outline=RAINBOW[(self.frame // 2) % len(RAINBOW)], width=2)

        for x, wy, _, _, life, col in self.particles:
            r = 2 + life / 10
            y = self.sy(wy)
            c.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="")
        for x, y, text, col, _ in self.texts:
            self.shadow_text(x, y, text, col, (FONT_NUM, 13, "bold"))

    def draw_minimap(self):
        c = self.cv
        c.create_rectangle(0, 0, FIELD_L, H, fill="#0d0d0d", outline="")
        x, top, bot = 30, 80, 680
        c.create_line(x, top, x, bot, fill="#424242", width=8)
        for i in range(4):
            for j in range(2):
                col = "#ffffff" if (i + j) % 2 == 0 else "#000000"
                c.create_rectangle(x - 8 + i * 4, top - 16 + j * 4, x - 4 + i * 4, top - 12 + j * 4,
                                   fill=col, outline="")
        c.create_line(x - 8, top - 16, x - 8, top + 2, fill="#bdbdbd", width=2)
        c.create_text(x, top - 30, text="GOAL", fill="#ffffff", font=(FONT_NUM, 8, "bold"))
        c.create_text(x, bot + 16, text="START", fill="#ffffff", font=(FONT_NUM, 8, "bold"))
        frac = max(0.0, min(1.0, self.d / self.L))
        y = bot - (bot - top) * frac
        c.create_rectangle(x - 6, y - 9, x + 6, y + 9, fill="#e53935", outline="#ffffff")
        for e in self.enemies:
            if e["kind"] == "rival" and not e["dead"]:
                ry = bot - (bot - top) * max(0.0, min(1.0, e["wy"] / self.L))
                c.create_rectangle(x - 4, ry - 6, x + 4, ry + 6, fill="#212121", outline="#ffd54f")
        c.create_text(x, 40, text=f"{int(frac * 100)}%", fill="#ffd54f", font=(FONT_NUM, 10, "bold"))

    def draw_hud(self):
        c = self.cv
        x0, cx = FIELD_R, (FIELD_R + W) / 2
        c.create_rectangle(x0, 0, W, H, fill="#000000", outline="")
        c.create_line(x0 + 1, 0, x0 + 1, H, fill="#333333", width=2)
        c.create_text(x0 + 16, 28, anchor="w", text="1P", fill="#ff5252", font=(FONT_NUM, 14, "bold"))
        c.create_text(W - 14, 56, anchor="e", text=f"{int(self.score):07d}", fill="#ffffff",
                      font=(FONT_NUM, 18, "bold"))
        c.create_text(x0 + 16, 92, anchor="w", text="HI", fill="#ffd54f", font=(FONT_NUM, 14, "bold"))
        c.create_text(W - 14, 118, anchor="e", text=f"{max(self.top_score(), int(self.score)):07d}",
                      fill="#ffd54f", font=(FONT_NUM, 16, "bold"))

        c.create_text(W - 14, 180, anchor="e", text=f"{int(self.v)}", fill="#ffffff", font=(FONT_NUM, 30, "bold"))
        c.create_text(W - 14, 212, anchor="e", text="km/h", fill="#bdbdbd", font=(FONT_NUM, 12))
        for i, (label, on) in enumerate((("LOW", not self.gear_hi), ("HIGH", self.gear_hi))):
            bx = x0 + 14 + i * 62
            col = "#69f0ae" if on and self.v > 0 else "#424242"
            c.create_rectangle(bx, 236, bx + 54, 260, outline=col, width=2, fill="#1b1b1b")
            c.create_text(bx + 27, 248, text=label, fill=col, font=(FONT_NUM, 11, "bold"))

        low = self.fuel < 15
        blink = low and (self.frame // 15) % 2 == 0
        c.create_rectangle(x0 + 14, 290, x0 + 74, 312, outline="#ff5252", width=2)
        c.create_text(x0 + 44, 301, text="FUEL", fill="#ff5252", font=(FONT_NUM, 11, "bold"))
        c.create_text(W - 14, 338, anchor="e", text=f"{int(math.ceil(self.fuel)):03d}",
                      fill="#ff5252" if blink else "#ffffff", font=(FONT_NUM, 22, "bold"))
        c.create_rectangle(x0 + 14, 360, W - 14, 372, fill="#1b1b1b", outline="#424242")
        fw = (W - 14 - x0 - 14) * self.fuel / FUEL_MAX
        c.create_rectangle(x0 + 15, 361, x0 + 15 + fw, 371,
                           fill="#ff5252" if low else "#ffb300", outline="")

        c.create_text(x0 + 16, 410, anchor="w", text=f"STAGE {self.stage + 1}/{len(STAGES)}",
                      fill="#4fc3f7", font=(FONT_NUM, 13, "bold"))
        c.create_text(x0 + 16, 434, anchor="w", text=self.st["th"], fill="#ffffff", font=(FONT_TH, 12, "bold"))
        c.create_text(x0 + 16, 456, anchor="w", text=DIFFS[self.diff]["name"], fill="#9e9e9e",
                      font=(FONT_NUM, 10, "bold"))
        c.create_text(x0 + 16, 490, anchor="w", text="TIME", fill="#9e9e9e", font=(FONT_NUM, 10, "bold"))
        c.create_text(W - 14, 512, anchor="e", text=self.fmt_time(self.time), fill="#ffffff",
                      font=(FONT_NUM, 15, "bold"))

        # จำนวนครั้งที่ยังชนได้ (รถสีแดง = เหลือ, สีเทา = ใช้ไปแล้ว)
        c.create_text(x0 + 16, 538, anchor="w", text="CRASH", fill="#9e9e9e", font=(FONT_NUM, 10, "bold"))
        c.create_text(W - 14, 538, anchor="e", text=f"{self.lives}/{MAX_CRASHES}",
                      fill="#ff5252" if self.lives <= 1 else "#ffffff", font=(FONT_NUM, 10, "bold"))
        for i in range(MAX_CRASHES):
            ix = x0 + 25 + i * 23
            alive = i < self.lives
            c.create_rectangle(ix - 7, 552, ix + 7, 572, fill="#e53935" if alive else "#2a2a2a",
                               outline="#ffffff" if alive else "#424242")
            c.create_rectangle(ix - 5, 556, ix + 5, 561, fill="#9fd3ff" if alive else "#333333", outline="")
            if not alive:
                c.create_line(ix - 7, 552, ix + 7, 572, fill="#ff5252", width=2)
                c.create_line(ix + 7, 552, ix - 7, 572, fill="#ff5252", width=2)

        hints = ["←→  เลี้ยว", "↑ / Z  เกียร์ต่ำ", "Shift / X  เกียร์สูง", "↓ / C  เบรก",
                 "P พัก   M เสียง"]
        for i, h in enumerate(hints):
            c.create_text(x0 + 14, 592 + i * 20, anchor="w", text=h, fill="#757575", font=(FONT_TH, 9))
        c.create_text(cx, 700, text="เสียง: " + ("เปิด" if self.sound.enabled else "ปิด"),
                      fill="#616161", font=(FONT_TH, 9))

    @staticmethod
    def fmt_time(frames):
        sec = frames / 60
        return f"{int(sec // 60)}:{sec % 60:04.1f}"

    def dim(self):
        self.cv.create_rectangle(FIELD_L, 0, FIELD_R, H, fill="#000000", stipple="gray50", outline="")

    def banner(self, title, sub, color, y=300):
        c = self.cv
        c.create_rectangle(FIELD_L, y - 60, FIELD_R, y + 60, fill="#000000", stipple="gray75", outline="")
        self.shadow_text(FIELD_CX, y - 18, title, color, (FONT_TITLE, 38))
        c.create_text(FIELD_CX, y + 30, text=sub, fill="#ffffff", font=(FONT_TH, 13, "bold"))

    def draw_credit_button(self, cx, cy):
        c = self.cv
        hover = self.credit_hover
        item = c.create_text(cx, cy, text=f"พัฒนาโดย {DEVELOPER}  |  GitHub ↗", font=(FONT_TH, 10, "bold"),
                             fill="#15181d" if hover else "#ffd54f")
        x0, y0, x1, y1 = c.bbox(item)
        box = (x0 - 12, y0 - 4, x1 + 12, y1 + 4)
        rect = c.create_rectangle(*box, fill="#ffd54f" if hover else "#263238", outline="#ffd54f", width=2)
        c.tag_lower(rect, item)
        self.credit_box = box

    def draw_title(self):
        c = self.cv
        self.dim()
        self.shadow_text(FIELD_CX, 105, "ROAD", "#ff5252", (FONT_TITLE, 60, "italic"))
        self.shadow_text(FIELD_CX, 170, "CHASER", "#ffd54f", (FONT_TITLE, 60, "italic"))
        c.create_text(FIELD_CX, 225, text="ถนนนักซิ่ง", fill="#ffffff", font=(FONT_TH, 18, "bold"))
        self.draw_vehicle(FIELD_CX, 280, "player", "#e53935", 0)

        unlocked = self.save["unlocked"]
        values = {
            "start": "เริ่มเกม  START",
            "stage": f"ด่าน:  ◀ {self.sel_stage + 1}. {STAGES[self.sel_stage]['th']} ▶",
            "diff": f"ความยาก:  ◀ {DIFFS[self.diff]['th']} ({DIFFS[self.diff]['name']}) ▶",
            "sound": "เสียง:  ◀ " + ("เปิด" if self.sound.enabled else "ปิด") + " ▶",
            "howto": "วิธีเล่น",
            "scores": "ตารางคะแนนสูงสุด",
        }
        for i, item in enumerate(MENU):
            y = 345 + i * 40
            sel = i == self.menu_idx
            if sel:
                c.create_rectangle(FIELD_L + 30, y - 16, FIELD_R - 30, y + 16, fill="#263238", outline="#ffd54f",
                                   width=2)
            c.create_text(FIELD_CX, y, text=values[item], fill="#ffd54f" if sel else "#ffffff",
                          font=(FONT_TH, 14 if item == "start" else 12, "bold"))
        c.create_text(FIELD_CX, 595, text=f"ปลดล็อกแล้ว {unlocked + 1}/{len(STAGES)} ด่าน   ↑↓ เลือก   Enter ตกลง",
                      fill="#cfd8dc", font=(FONT_TH, 10))
        c.create_text(FIELD_CX, 620, text="Inspired by Konami's Road Fighter (1984)", fill="#9e9e9e",
                      font=(FONT_NUM, 9))
        self.draw_credit_button(FIELD_CX, 670)

    def draw_howto(self):
        c = self.cv
        c.create_rectangle(FIELD_L, 0, FIELD_R, H, fill="#101418", outline="")
        self.shadow_text(FIELD_CX, 40, "วิธีเล่น", "#ffd54f", (FONT_TH, 22, "bold"))
        lines = [
            "ขับให้ถึงเส้นชัย (GOAL) ก่อนน้ำมันหมด",
            f"ชนขอบถนน / เกาะกลาง / รถบรรทุก / หิน = ระเบิด (ได้ {MAX_CRASHES} ครั้ง)",
            "ชนรถเก๋ง = รถหมุน กดเลี้ยวสวนทางเพื่อตั้งหลัก",
            "↑/Z เกียร์ต่ำ (200)  +  Shift/X เกียร์สูง (400 km/h)",
            "เทคนิค: ออกตัวด้วยเกียร์ต่ำ แล้วค่อยกดเกียร์สูง",
        ]
        for i, s in enumerate(lines):
            c.create_text(FIELD_CX, 82 + i * 26, text=s, fill="#ffffff", font=(FONT_TH, 11))
        legend = [
            ("sedan", "#f4c430", "รถเหลือง: วิ่งตรง"),
            ("sedan", "#1e6be0", "รถน้ำเงิน: เปลี่ยนเลนมาขวาง"),
            ("sedan", "#9b59b6", "รถม่วง: ส่ายไปมา"),
            ("truck", "#2e7d32", "รถบรรทุก: ห้ามชนเด็ดขาด!"),
            ("fuel", None, "รถสีรุ้ง: ชนเพื่อเติมน้ำมัน +1000"),
            ("rival", "#212121", "คู่แข่ง: ไล่มาจากด้านหลัง ชอบเบียด"),
            ("oil", None, "คราบน้ำมัน: ทำให้รถลื่นหมุน"),
            ("star", None, "ดาว: อมตะชั่วคราว ชนรถได้คะแนน"),
        ]
        for i, (kind, col, text) in enumerate(legend):
            y = 240 + i * 52
            x = FIELD_L + 50
            if kind == "fuel":
                self.draw_vehicle(x, y, "sedan", RAINBOW[(self.frame // 5) % len(RAINBOW)], 0, shadow=False)
            elif kind == "oil":
                c.create_oval(x - 16, y - 9, x + 16, y + 9, fill="#141414", outline="#555555")
            elif kind == "star":
                c.create_polygon(transform(STAR_PTS, x, y, self.frame * 4), fill="#ffea00", outline="#ff9100")
            elif kind == "truck":
                self.draw_vehicle(x + 6, y, "truck", col, 90, shadow=False)
            else:
                self.draw_vehicle(x, y, kind, col, 0, shadow=False)
            c.create_text(x + 62, y, anchor="w", text=text, fill="#ffffff", font=(FONT_TH, 11))
        c.create_text(FIELD_CX, 700, text="กด Enter / Esc เพื่อกลับ", fill="#69f0ae", font=(FONT_TH, 11, "bold"))

    def draw_scores(self):
        c = self.cv
        c.create_rectangle(FIELD_L, 0, FIELD_R, H, fill="#101418", outline="")
        self.shadow_text(FIELD_CX, 60, "HIGH SCORES", "#ffd54f", (FONT_TITLE, 34))
        scores = self.save["scores"]
        if not scores:
            c.create_text(FIELD_CX, 200, text="ยังไม่มีสถิติ", fill="#9e9e9e", font=(FONT_TH, 14))
        for i, s in enumerate(scores):
            y = 140 + i * 42
            col = "#ffd54f" if i == 0 else "#ffffff"
            c.create_text(FIELD_L + 40, y, anchor="w", text=f"{i + 1}.", fill=col, font=(FONT_NUM, 16, "bold"))
            c.create_text(FIELD_L + 80, y, anchor="w", text=f"{int(s['score']):07d}", fill=col,
                          font=(FONT_NUM, 16, "bold"))
            c.create_text(FIELD_R - 30, y, anchor="e", text=f"ด่าน {s.get('stage', '?')}  {s.get('diff', '')}",
                          fill="#bdbdbd", font=(FONT_TH, 11))
        c.create_text(FIELD_CX, 395, text="เวลาที่ดีที่สุดแต่ละด่าน", fill="#4fc3f7", font=(FONT_TH, 14, "bold"))
        for i, st in enumerate(STAGES):
            y = 430 + i * 30
            t = self.save["best_time"].get(str(i))
            c.create_text(FIELD_L + 40, y, anchor="w", text=f"{i + 1}. {st['th']}", fill="#ffffff",
                          font=(FONT_TH, 11))
            c.create_text(FIELD_R - 30, y, anchor="e", text=self.fmt_time(t) if t else "-",
                          fill="#ffffff", font=(FONT_NUM, 12, "bold"))
        c.create_text(FIELD_CX, 700, text="กด Enter / Esc เพื่อกลับ", fill="#69f0ae", font=(FONT_TH, 11, "bold"))

    def draw_intro(self):
        c = self.cv
        c.create_rectangle(FIELD_L, 200, FIELD_R, 330, fill="#000000", stipple="gray75", outline="")
        self.shadow_text(FIELD_CX, 235, f"STAGE {self.stage + 1}", "#ffd54f", (FONT_TITLE, 40))
        c.create_text(FIELD_CX, 280, text=self.st["name"], fill="#ffffff", font=(FONT_NUM, 16, "bold"))
        c.create_text(FIELD_CX, 308, text=self.st["th"], fill="#4fc3f7", font=(FONT_TH, 14, "bold"))
        if self.intro_t <= 180:
            n = math.ceil(self.intro_t / 60)
            self.shadow_text(FIELD_CX, 420, str(n), "#ffffff", (FONT_TITLE, 70))
        else:
            c.create_text(FIELD_CX, 420, text="READY", fill="#ffffff", font=(FONT_TITLE, 36))

    def draw_goal(self):
        c = self.cv
        c.create_rectangle(FIELD_L, 170, FIELD_R, 470, fill="#000000", stipple="gray75", outline="")
        self.shadow_text(FIELD_CX, 210, "STAGE CLEAR!", "#69f0ae", (FONT_TITLE, 40))
        rows = [
            ("เวลา", self.fmt_time(self.time) + ("  NEW!" if self.new_best_time else "")),
            ("ชน", f"{self.crashes} ครั้ง"),
            ("แซงรถ", f"{self.passed} คัน"),
            ("โบนัสน้ำมัน", f"{self.tally_bonus}"),
        ]
        for i, (k, v) in enumerate(rows):
            y = 270 + i * 34
            c.create_text(FIELD_L + 60, y, anchor="w", text=k, fill="#ffffff", font=(FONT_TH, 13, "bold"))
            c.create_text(FIELD_R - 60, y, anchor="e", text=v,
                          fill="#ffd54f" if "NEW" in v else "#ffffff", font=(FONT_NUM, 15, "bold"))
        if self.tally_done and (self.frame // 20) % 2 == 0:
            nxt = "ไปด่านต่อไป" if self.stage + 1 < len(STAGES) else "ดูตอนจบ"
            c.create_text(FIELD_CX, 445, text=f"กด Enter เพื่อ{nxt}", fill="#69f0ae", font=(FONT_TH, 14, "bold"))

    def draw_over(self):
        c = self.cv
        self.dim()
        self.shadow_text(FIELD_CX, 230, "GAME OVER", "#ff5252", (FONT_TITLE, 50))
        reason = f"ชนครบ {MAX_CRASHES} ครั้ง!" if self.over_reason == "crash" else "น้ำมันหมด!"
        c.create_text(FIELD_CX, 290, text=reason, fill="#ffffff", font=(FONT_TH, 16, "bold"))
        c.create_text(FIELD_CX, 330, text=f"คะแนน {int(self.score):07d}", fill="#ffd54f", font=(FONT_NUM, 18, "bold"))
        if self.over_rank:
            c.create_text(FIELD_CX, 365, text=f"ติดอันดับที่ {self.over_rank}!", fill="#69f0ae",
                          font=(FONT_TH, 14, "bold"))
        if (self.frame // 20) % 2 == 0:
            c.create_text(FIELD_CX, 430, text="กด Enter เพื่อ CONTINUE ด่านนี้", fill="#69f0ae",
                          font=(FONT_TH, 14, "bold"))
        c.create_text(FIELD_CX, 460, text=f"(คะแนนเริ่มใหม่ ชนได้ {MAX_CRASHES} ครั้ง)   Esc = หน้าแรก", fill="#bdbdbd",
                      font=(FONT_TH, 11))

    def draw_ending(self):
        c = self.cv
        c.create_rectangle(FIELD_L, 0, FIELD_R, H, fill="#000000", stipple="gray75", outline="")
        self.shadow_text(FIELD_CX, 170, "CONGRATULATIONS!", "#ffd54f", (FONT_TITLE, 32))
        c.create_text(FIELD_CX, 225, text="คุณพิชิตครบทุกเส้นทางแล้ว!", fill="#ffffff", font=(FONT_TH, 16, "bold"))
        self.draw_vehicle(FIELD_CX, 300, "player", RAINBOW[(self.frame // 6) % len(RAINBOW)], 0)
        c.create_text(FIELD_CX, 380, text=f"คะแนนรวม {int(self.score):07d}", fill="#ffd54f",
                      font=(FONT_NUM, 20, "bold"))
        c.create_text(FIELD_CX, 412, text=f"ความยาก: {DIFFS[self.diff]['th']}", fill="#bdbdbd", font=(FONT_TH, 12))
        if self.end_rank:
            c.create_text(FIELD_CX, 445, text=f"ติดอันดับที่ {self.end_rank}!", fill="#69f0ae",
                          font=(FONT_TH, 14, "bold"))
        c.create_text(FIELD_CX, 520, text="กด Enter เพื่อกลับหน้าแรก", fill="#69f0ae", font=(FONT_TH, 13, "bold"))
        self.draw_credit_button(FIELD_CX, 600)


def main():
    root = tk.Tk()
    RoadChaser(root)
    root.mainloop()


if __name__ == "__main__":
    main()
