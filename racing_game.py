"""
เกมรถแข่ง (Racing Game) - ใช้แค่ tkinter ไม่ต้องติดตั้ง library เพิ่ม
พัฒนาโดย Uncle Engineer

วิธีเล่น:
    ← / →  หรือ A / D   : เลี้ยวซ้าย / ขวา
    ↑ / W               : เร่งความเร็ว
    ↓ / S               : เบรก
    Shift / Space       : ไนโตร (ระหว่างแข่ง)
    P                   : หยุดชั่วคราว
    C                   : เปลี่ยนรถ (หน้าจบเกม)
    Esc                 : ออกจากเกม

หลบรถคันอื่น เก็บเหรียญ $ ถังไนโตร N และโล่ S
แซงแบบเฉียดฉิวได้โบนัส ยิ่งวิ่งเร็ว คะแนนยิ่งขึ้นเร็ว!
"""

import json
import math
import os
import random
import tkinter as tk

# ---------------- ค่าคงที่ ----------------
W, H = 480, 720
ROAD_L, ROAD_R = 60, 420
LANES = 4
LANE_W = (ROAD_R - ROAD_L) / LANES
FRAME_MS = 16
FONT = "Tahoma"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "racing_save.json")
OLD_HS_FILE = os.path.join(BASE_DIR, "racing_highscore.txt")

NITRO_MAX = 100
SHIELD_FRAMES = 480

# รถที่ผู้เล่นเลือกได้ (ค่าพลัง 1-5)
CARS = [
    {"style": "sport", "name": "สปอร์ต", "en": "SPEEDSTER", "desc": "สมดุลทุกด้าน เหมาะกับมือใหม่",
     "color": "#e53935", "w": 46, "h": 86, "top": 3, "accel": 3, "handle": 3, "nitro": 3},
    {"style": "formula", "name": "ฟอร์มูล่า", "en": "FORMULA", "desc": "ความเร็วสูงสุดเหนือใคร แต่คุมยาก",
     "color": "#1e88e5", "w": 44, "h": 92, "top": 5, "accel": 4, "handle": 2, "nitro": 2},
    {"style": "muscle", "name": "มัสเซิล", "en": "MUSCLE", "desc": "อัตราเร่งแรง แต่ตัวใหญ่ เลี้ยวหนัก",
     "color": "#ff8f00", "w": 52, "h": 92, "top": 4, "accel": 5, "handle": 1, "nitro": 3},
    {"style": "mini", "name": "มินิ", "en": "MINI", "desc": "ตัวเล็ก คล่องตัว หลบง่าย แต่ไม่เร็ว",
     "color": "#7cb342", "w": 38, "h": 66, "top": 2, "accel": 3, "handle": 5, "nitro": 2},
    {"style": "police", "name": "ตำรวจ", "en": "POLICE", "desc": "ไนโตรจัดเต็ม พร้อมไฟไซเรน",
     "color": "#fafafa", "w": 46, "h": 88, "top": 3, "accel": 3, "handle": 4, "nitro": 5},
]
STAT_LABELS = [("top", "ความเร็วสูงสุด"), ("accel", "อัตราเร่ง"),
               ("handle", "การควบคุม"), ("nitro", "ไนโตร")]

ENEMY_TYPES = [
    {"style": "sedan", "w": 46, "h": 86, "weight": 8},
    {"style": "truck", "w": 50, "h": 130, "weight": 2},
]
ENEMY_COLORS = ["#1e88e5", "#43a047", "#fdd835", "#8e24aa", "#fb8c00",
                "#00acc1", "#f5f5f5", "#6d4c41", "#3949ab", "#ec407a"]

# ตำแหน่งในหน้าเลือกรถ
PREVIEW_BOX = (90, 105, 390, 345)
THUMB_Y = 630


def lane_center(i):
    return ROAD_L + LANE_W * i + LANE_W / 2


class RacingGame:
    def __init__(self, root):
        self.root = root
        root.title("เกมรถแข่ง - Racing Game")
        root.resizable(False, False)
        self.cv = tk.Canvas(root, width=W, height=H, bg="#3b8a3b", highlightthickness=0)
        self.cv.pack()

        self.keys = set()
        root.bind("<KeyPress>", self.on_press)
        root.bind("<KeyRelease>", self.on_release)
        root.bind("<FocusOut>", self.on_focus_out)
        self.cv.bind("<Button-1>", self.on_click)

        self.save = self.load_save()
        self.best = self.save["best"]
        self.sel = self.save["car"]
        self.car = CARS[self.sel]
        self.frame = 0
        self.state = "select"   # select, count, play, pause, crash, over
        self.reset()
        self.loop()

    # ---------------- บันทึกข้อมูล ----------------
    def load_save(self):
        data = {"best": 0, "car": 0, "car_best": {}}
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, ValueError):
            # ย้ายคะแนนจากไฟล์เวอร์ชันเก่า
            try:
                with open(OLD_HS_FILE, "r", encoding="utf-8") as f:
                    data["best"] = int(f.read().strip() or 0)
            except (OSError, ValueError):
                pass
        if not isinstance(data.get("car"), int) or not 0 <= data["car"] < len(CARS):
            data["car"] = 0
        if not isinstance(data.get("car_best"), dict):
            data["car_best"] = {}
        if not isinstance(data.get("best"), int):
            data["best"] = 0
        return data

    def write_save(self):
        self.save["best"] = self.best
        self.save["car"] = self.sel
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.save, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def car_best(self, car):
        return int(self.save["car_best"].get(car["style"], 0))

    # ---------------- เริ่มเกมใหม่ ----------------
    def reset(self):
        self.px = lane_center(1)
        self.py = H - 120
        self.vx = 0.0
        self.speed = 6.0
        self.distance = 0.0
        self.bonus = 0
        self.coins_got = 0
        self.passed = 0
        self.near_misses = 0
        self.nitro = 50.0
        self.boosting = False
        self.shield = 0
        self.invuln = 0
        self.enemies = []
        self.pickups = []
        self.particles = []
        self.texts = []
        self.dash_off = 0.0
        self.spawn_cd = 60
        self.pickup_cd = 90
        self.crash_timer = 0
        self.count_t = 0
        self.go_t = 0
        self.shake = 0
        self.new_record = False
        # รถแต่ละเลนวิ่งความเร็วคงที่ (ไม่ชนกันเอง)
        self.lane_speed = [random.uniform(1.5, 4.5) for _ in range(LANES)]
        self.trees = [self.make_tree(random.uniform(0, H)) for _ in range(14)]

    def start_race(self):
        self.car = CARS[self.sel]
        self.write_save()
        self.reset()
        self.state = "count"
        self.count_t = 180

    def make_tree(self, y):
        if random.random() < 0.5:
            x = random.uniform(8, ROAD_L - 22)
        else:
            x = random.uniform(ROAD_R + 22, W - 8)
        return [x, y, random.uniform(12, 20)]

    @property
    def score(self):
        return int(self.distance / 10) + self.bonus

    # ---------------- อินพุต ----------------
    def on_press(self, e):
        k = e.keysym.lower()
        self.keys.add(k)
        if k == "escape":
            self.root.destroy()
        elif self.state == "select":
            if k in ("left", "a"):
                self.sel = (self.sel - 1) % len(CARS)
            elif k in ("right", "d"):
                self.sel = (self.sel + 1) % len(CARS)
            elif k in ("space", "return"):
                self.start_race()
        elif self.state == "over":
            if k in ("space", "return"):
                self.start_race()
            elif k == "c":
                self.state = "select"
        elif k == "p":
            if self.state == "play":
                self.state = "pause"
            elif self.state == "pause":
                self.state = "play"

    def on_release(self, e):
        self.keys.discard(e.keysym.lower())

    def on_focus_out(self, _e):
        # กันปุ่มค้างเวลาสลับหน้าต่าง
        self.keys.clear()
        if self.state == "play":
            self.state = "pause"

    def on_click(self, e):
        if self.state != "select":
            return
        slot = W / len(CARS)
        if THUMB_Y - 40 <= e.y <= THUMB_Y + 40:
            self.sel = min(len(CARS) - 1, int(e.x // slot))
            return
        x0, y0, x1, y1 = PREVIEW_BOX
        if x0 <= e.x <= x1 and y0 <= e.y <= y1:
            self.start_race()
        elif y0 <= e.y <= y1:
            self.sel = (self.sel + (1 if e.x > x1 else -1)) % len(CARS)

    def held(self, *names):
        return any(n in self.keys for n in names)

    # ---------------- ลูปหลัก ----------------
    def loop(self):
        self.frame += 1
        self.update()
        self.draw()
        self.root.after(FRAME_MS, self.loop)

    def update(self):
        if self.state == "play":
            self.update_play()
        elif self.state == "count":
            self.count_t -= 1
            if self.count_t <= 0:
                self.state = "play"
                self.go_t = 45
        elif self.state == "crash":
            self.update_effects()
            self.crash_timer -= 1
            if self.crash_timer <= 0:
                self.state = "over"
        elif self.state == "select":
            # ฉากหลังวิ่งเบาๆ ตอนเลือกรถ
            self.scroll_world(4)
        elif self.state == "over":
            self.update_effects()

    def update_play(self):
        car = self.car
        # ความเร็ว: ยิ่งไกลยิ่งเร็วขึ้น และขึ้นกับสเปกรถ
        min_spd = min(5 + self.distance / 5000, 12)
        max_spd = min(12 + self.distance / 3000, 22) * (1 + (car["top"] - 3) * 0.08)
        accel = 0.15 * (1 + (car["accel"] - 3) * 0.2)

        self.boosting = self.held("shift_l", "shift_r", "space") and self.nitro > 0
        if self.boosting:
            self.nitro = max(0.0, self.nitro - 0.8)
            self.speed = min(max_spd + 6, self.speed + accel * 2.5)
        else:
            if self.held("up", "w"):
                self.speed += accel
            elif self.held("down", "s"):
                self.speed -= 0.35
            else:
                self.speed -= 0.03
            if self.speed > max_spd:   # ค่อยๆ ลดหลังหมดไนโตร
                self.speed = max(max_spd, self.speed - 0.25)
        self.speed = max(min_spd, self.speed)

        # เลี้ยวแบบมีแรงเฉื่อย รถที่ควบคุมดีจะตอบสนองไว
        h01 = (car["handle"] - 1) / 4
        max_lat = (4 + self.speed * 0.22) * (0.8 + 0.4 * h01)
        grip = 0.10 + 0.25 * h01
        target = 0.0
        if self.held("left", "a"):
            target -= max_lat
        if self.held("right", "d"):
            target += max_lat
        self.vx += (target - self.vx) * grip
        self.px += self.vx
        lo, hi = ROAD_L + car["w"] / 2 + 4, ROAD_R - car["w"] / 2 - 4
        if self.px < lo or self.px > hi:
            self.px = max(lo, min(hi, self.px))
            self.vx = 0.0

        self.distance += self.speed
        self.scroll_world(self.speed)
        if self.shield > 0:
            self.shield -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.go_t > 0:
            self.go_t -= 1

        # รถศัตรู
        for en in self.enemies:
            en["prev"] = en["y"]
            en["y"] += self.speed - en["spd"]
        before = len(self.enemies)
        self.enemies = [en for en in self.enemies if en["y"] - en["h"] / 2 < H]
        passed = before - len(self.enemies)
        self.passed += passed
        self.bonus += passed * 5

        self.spawn_cd -= 1
        if self.spawn_cd <= 0:
            self.spawn_enemy()
            base = max(18, 55 - self.distance / 800)
            self.spawn_cd = int(random.uniform(base * 0.7, base * 1.3))

        # ไอเท็ม
        for it in self.pickups:
            it["y"] += self.speed
        self.pickups = [it for it in self.pickups if it["y"] < H + 30]
        self.pickup_cd -= 1
        if self.pickup_cd <= 0:
            self.spawn_pickup()
            self.pickup_cd = random.randint(50, 120)

        # ชน
        pl, pt, pr, pb = self.player_box()
        for en in list(self.enemies):
            ex, ey, ew, eh = lane_center(en["lane"]), en["y"], en["w"], en["h"]
            if (pl < ex + ew / 2 - 6 and pr > ex - ew / 2 + 6 and
                    pt < ey + eh / 2 - 6 and pb > ey - eh / 2 + 6):
                if self.invuln > 0:
                    continue
                if self.shield > 0:
                    self.enemies.remove(en)
                    self.shield = 0
                    self.invuln = 40
                    self.shake = 8
                    self.bonus += 30
                    self.explode(ex, ey, 35)
                    self.float_text(ex, ey, "กระเด็น! +30", "#40c4ff")
                    continue
                self.crash()
                return

        # แซงเฉียดฉิว
        for en in self.enemies:
            if not en.get("nm") and en["prev"] < self.py <= en["y"]:
                en["nm"] = True
                gap = abs(lane_center(en["lane"]) - self.px) - (en["w"] + car["w"]) / 2
                if gap < 16:
                    self.near_misses += 1
                    self.bonus += 25
                    self.float_text(self.px, self.py - 60, "เฉียด! +25", "#ff80ab")

        # เก็บไอเท็ม
        remaining = []
        for it in self.pickups:
            ix = lane_center(it["lane"])
            if pl - 12 < ix < pr + 12 and pt - 12 < it["y"] < pb + 12:
                self.collect(it, ix)
            else:
                remaining.append(it)
        self.pickups = remaining
        self.update_effects()

    def collect(self, it, x):
        kind = it["kind"]
        if kind == "coin":
            self.coins_got += 1
            self.bonus += 50
            self.nitro = min(NITRO_MAX, self.nitro + 4 + 2 * self.car["nitro"])
            self.sparkle(x, it["y"], "#ffeb3b")
            self.float_text(x, it["y"], "+50", "#ffeb3b")
        elif kind == "nitro":
            self.nitro = min(NITRO_MAX, self.nitro + 20 + 6 * self.car["nitro"])
            self.sparkle(x, it["y"], "#ff7043")
            self.float_text(x, it["y"], "NITRO!", "#ff7043")
        elif kind == "shield":
            self.shield = SHIELD_FRAMES
            self.sparkle(x, it["y"], "#40c4ff")
            self.float_text(x, it["y"], "โล่!", "#40c4ff")

    def scroll_world(self, spd):
        self.dash_off = (self.dash_off + spd) % 60
        for t in self.trees:
            t[1] += spd
            if t[1] > H + 30:
                t[:] = self.make_tree(random.uniform(-80, -20))

    def player_box(self):
        w, h = self.car["w"], self.car["h"]
        return (self.px - w / 2 + 4, self.py - h / 2 + 4,
                self.px + w / 2 - 4, self.py + h / 2 - 4)

    def spawn_enemy(self):
        # เลนที่มีรถอยู่ใกล้ด้านบน -> ห้ามเกิดซ้อน
        busy_top = {en["lane"] for en in self.enemies if en["y"] - en["h"] / 2 < 40}
        # ห้ามปิดทุกเลน ต้องเหลือทางหนีอย่างน้อย 1 เลน
        band = {en["lane"] for en in self.enemies if en["y"] - en["h"] / 2 < 300}
        free = [i for i in range(LANES) if i not in busy_top]
        random.shuffle(free)
        for lane in free:
            if len(band | {lane}) < LANES:
                kind = random.choices(ENEMY_TYPES, weights=[t["weight"] for t in ENEMY_TYPES])[0]
                self.enemies.append({
                    "lane": lane,
                    "y": -kind["h"] / 2 - 10,
                    "prev": -kind["h"] / 2 - 10,
                    "spd": self.lane_speed[lane],
                    "style": kind["style"],
                    "w": kind["w"],
                    "h": kind["h"],
                    "color": random.choice(ENEMY_COLORS),
                })
                return

    def spawn_pickup(self):
        lane = random.randrange(LANES)
        for en in self.enemies:
            if en["lane"] == lane and en["y"] - en["h"] / 2 < 180:
                return
        r = random.random()
        kind = "shield" if r < 0.08 else "nitro" if r < 0.25 else "coin"
        self.pickups.append({"lane": lane, "y": -20, "kind": kind})

    def crash(self):
        self.state = "crash"
        self.crash_timer = 70
        self.shake = 18
        self.boosting = False
        self.explode(self.px, self.py - 20, 60)
        style = self.car["style"]
        if self.score > self.car_best(self.car):
            self.save["car_best"][style] = self.score
        if self.score > self.best:
            self.best = self.score
            self.new_record = True
        self.write_save()

    def explode(self, x, y, n):
        for _ in range(n):
            self.particles.append([
                x, y, random.uniform(-6, 6), random.uniform(-7, 3), random.randint(25, 60),
                random.choice(["#ff5722", "#ffc107", "#ff9800", "#f44336", "#555555"]),
            ])

    def sparkle(self, x, y, color):
        for _ in range(12):
            self.particles.append([x, y, random.uniform(-3, 3), random.uniform(-3, 3),
                                   random.randint(10, 22), color])

    def float_text(self, x, y, text, color):
        self.texts.append([x, y, text, color, 50])

    def update_effects(self):
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.15
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        for t in self.texts:
            t[1] -= 1.2
            t[4] -= 1
        self.texts = [t for t in self.texts if t[4] > 0]
        if self.shake > 0:
            self.shake -= 1

    # ---------------- วาด ----------------
    def draw(self):
        c = self.cv
        c.delete("all")
        self.draw_world()

        if self.state == "select":
            self.draw_select()
            return

        # รถผู้เล่น
        car = self.car
        if self.state in ("count", "play", "pause"):
            if self.boosting:
                self.draw_flame(self.px, self.py + car["h"] / 2)
            if self.invuln == 0 or (self.frame // 4) % 2 == 0:
                self.draw_car(self.px, self.py, car)
            if self.shield > 0 and (self.shield > 120 or (self.frame // 6) % 2 == 0):
                r = max(car["w"], car["h"]) / 2 + 10
                c.create_oval(self.px - r * 0.75, self.py - r, self.px + r * 0.75, self.py + r,
                              outline="#40c4ff", width=3)
        elif self.state == "crash" and self.crash_timer > 50:
            self.draw_car(self.px, self.py, car, color="#5d1f1f")

        for x, y, _, _, life, col in self.particles:
            r = 2 + life / 12
            c.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="")
        for x, y, text, col, _ in self.texts:
            c.create_text(x + 2, y + 2, text=text, fill="#000", font=(FONT, 15, "bold"))
            c.create_text(x, y, text=text, fill=col, font=(FONT, 15, "bold"))

        if self.shake > 0:
            m = self.shake / 2
            c.move("all", random.uniform(-m, m), random.uniform(-m, m))

        self.draw_hud()

        if self.state == "count":
            self.draw_countdown()
        elif self.state == "pause":
            self.overlay("หยุดชั่วคราว", "กด P เพื่อเล่นต่อ  |  Esc ออกจากเกม")
        elif self.state == "over":
            self.draw_game_over()
        elif self.state == "play" and self.go_t > 0:
            c.create_text(W / 2 + 3, H / 2 - 77, text="GO!", fill="#000", font=(FONT, 64, "bold"))
            c.create_text(W / 2, H / 2 - 80, text="GO!", fill="#69f0ae", font=(FONT, 64, "bold"))

    def draw_world(self):
        c = self.cv
        # ต้นไม้ริมทาง
        for x, y, s in self.trees:
            c.create_oval(x - s + 4, y - s + 6, x + s + 4, y + s + 6, fill="#2a6a2a", outline="")
            c.create_oval(x - s, y - s, x + s, y + s, fill="#1f7a1f", outline="#145214")
            c.create_oval(x - s / 2, y - s / 2 - 3, x + s / 3, y + s / 4 - 3, fill="#2e9e2e", outline="")

        # ถนน
        c.create_rectangle(ROAD_L, 0, ROAD_R, H, fill="#444", outline="")
        off = self.dash_off
        for y in range(-60, H + 60, 30):
            yy = y + (off % 60)
            color = "#e53935" if (y // 30) % 2 == 0 else "#ffffff"
            c.create_rectangle(ROAD_L - 10, yy, ROAD_L, yy + 30, fill=color, outline="")
            c.create_rectangle(ROAD_R, yy, ROAD_R + 10, yy + 30, fill=color, outline="")
        for i in range(1, LANES):
            x = ROAD_L + LANE_W * i
            for y in range(-60, H + 60, 60):
                yy = y + off
                c.create_rectangle(x - 3, yy, x + 3, yy + 32, fill="#eeeeee", outline="")

        # เส้นความเร็วตอนใช้ไนโตร
        if self.boosting:
            for _ in range(10):
                x = random.uniform(ROAD_L + 5, ROAD_R - 5)
                y = random.uniform(50, H)
                c.create_line(x, y, x, y + random.uniform(30, 70), fill="#bbbbbb")

        for it in self.pickups:
            self.draw_pickup(lane_center(it["lane"]), it["y"], it["kind"])
        for en in self.enemies:
            self.draw_car(lane_center(en["lane"]), en["y"], en, color=en["color"])

    def draw_pickup(self, x, y, kind):
        c = self.cv
        if kind == "coin":
            c.create_oval(x - 13, y - 13, x + 13, y + 13, fill="#ffc107", outline="#b28704", width=3)
            c.create_text(x, y, text="$", fill="#8d6e00", font=(FONT, 12, "bold"))
        elif kind == "nitro":
            c.create_rectangle(x - 10, y - 15, x + 10, y + 15, fill="#ff5722", outline="#7f2a10", width=3)
            c.create_rectangle(x - 4, y - 19, x + 4, y - 15, fill="#9e9e9e", outline="")
            c.create_text(x, y + 1, text="N", fill="#ffffff", font=(FONT, 12, "bold"))
        elif kind == "shield":
            pulse = 2 * math.sin(self.frame * 0.2)
            r = 15 + pulse
            c.create_oval(x - r, y - r, x + r, y + r, fill="#0288d1", outline="#80d8ff", width=3)
            c.create_text(x, y, text="S", fill="#ffffff", font=(FONT, 12, "bold"))

    def draw_flame(self, x, y):
        c = self.cv
        ln = random.uniform(22, 38)
        c.create_polygon(x - 11, y, x + 11, y, x, y + ln, fill="#ff6d00", outline="")
        c.create_polygon(x - 6, y, x + 6, y, x, y + ln * 0.6, fill="#ffea00", outline="")

    def draw_car(self, x, y, car, color=None, scale=1.0):
        c = self.cv
        s = scale
        style = car["style"]
        color = color or car.get("color", "#e53935")
        hw, hh = car["w"] / 2, car["h"] / 2
        glass, glass2, dark = "#90caf9", "#64b5f6", "#1a1a1a"

        def rect(x0, y0, x1, y1, **kw):
            c.create_rectangle(x + x0 * s, y + y0 * s, x + x1 * s, y + y1 * s, **kw)

        def oval(x0, y0, x1, y1, **kw):
            c.create_oval(x + x0 * s, y + y0 * s, x + x1 * s, y + y1 * s, **kw)

        def poly(pts, **kw):
            c.create_polygon([x + p * s if i % 2 == 0 else y + p * s for i, p in enumerate(pts)], **kw)

        if style == "formula":
            rect(-hw + 6, -hh + 6, hw + 4, hh + 6, fill="#333", outline="")
            for y0, y1 in ((-hh + 10, -hh + 30), (hh - 32, hh - 8)):
                rect(-hw, y0, -hw + 10, y1, fill="#111", outline="")
                rect(hw - 10, y0, hw, y1, fill="#111", outline="")
            rect(-hw + 2, -hh, hw - 2, -hh + 6, fill=color, outline=dark, width=2)       # ปีกหน้า
            poly([-5, -hh + 4, 5, -hh + 4, 9, -hh + 32, 12, hh - 14, -12, hh - 14, -9, -hh + 32],
                 fill=color, outline=dark, width=2)
            rect(-15, -6, 15, 20, fill=color, outline=dark, width=2)                     # ไซด์พอด
            rect(-2, -hh + 6, 2, -6, fill="#ffffff", outline="")
            oval(-7, -14, 7, 6, fill="#222", outline=dark)                                # ห้องคนขับ
            oval(-5, -11, 5, -1, fill="#ffeb3b", outline=dark)                            # หมวกนักแข่ง
            rect(-hw + 4, hh - 10, hw - 4, hh, fill="#222", outline=dark)                # ปีกหลัง
            return

        if style == "truck":
            rect(-hw + 4, -hh + 6, hw + 4, hh + 6, fill="#333", outline="")
            for wy in (-hh + 12, 4, hh - 30):
                rect(-hw - 4, wy, -hw + 6, wy + 18, fill="#111", outline="")
                rect(hw - 6, wy, hw + 4, wy + 18, fill="#111", outline="")
            poly([-hw + 6, -hh, hw - 6, -hh, hw, -hh + 8, hw, -hh + 34, -hw, -hh + 34, -hw, -hh + 8],
                 fill=color, outline=dark, width=2)
            rect(-hw + 5, -hh + 8, hw - 5, -hh + 17, fill=glass, outline=dark)
            rect(-hw, -hh + 38, hw, hh, fill="#cfd8dc", outline=dark, width=2)
            for yy in range(int(-hh + 52), int(hh), 16):
                rect(-hw + 3, yy, hw - 3, yy + 1, fill="#90a4ae", outline="")
            rect(-hw + 4, -hh + 1, -hw + 12, -hh + 5, fill="#fff59d", outline="")
            rect(hw - 12, -hh + 1, hw - 4, -hh + 5, fill="#fff59d", outline="")
            rect(-hw + 3, hh - 5, -hw + 11, hh - 1, fill="#ff1744", outline="")
            rect(hw - 11, hh - 5, hw - 3, hh - 1, fill="#ff1744", outline="")
            return

        # รถทั่วไป: sport / muscle / mini / police / sedan
        rect(-hw + 4, -hh + 6, hw + 4, hh + 6, fill="#333", outline="")
        wl = 16 if car["h"] < 80 else 20
        for wy in (-hh + 10, hh - 10 - wl):
            rect(-hw - 4, wy, -hw + 6, wy + wl, fill="#111", outline="")
            rect(hw - 6, wy, hw + 4, wy + wl, fill="#111", outline="")
        poly([-hw + 8, -hh, hw - 8, -hh, hw, -hh + 14, hw, hh - 8, hw - 6, hh, -hw + 6, hh,
              -hw, hh - 8, -hw, -hh + 14], fill=color, outline=dark, width=2)

        if style == "police":
            rect(-hw + 3, -hh + 2, hw - 3, -hh + 18, fill="#212121", outline="")
            rect(-hw + 3, hh - 14, hw - 3, hh - 2, fill="#212121", outline="")
        elif style == "sport":
            rect(-5, -hh + 2, 5, hh - 2, fill="#ffffff", outline="")
        elif style == "muscle":
            for sx in (-10, 4):
                rect(sx, -hh + 2, sx + 6, hh - 2, fill="#212121", outline="")
            rect(-7, -hh + 8, 7, -hh + 17, fill="#424242", outline=dark)               # ช่องดักลม

        roof = "#fafafa" if style == "mini" else color
        poly([-hw + 7, -hh + 30, hw - 7, -hh + 30, hw - 10, -hh + 20, -hw + 10, -hh + 20],
             fill=glass, outline=dark)
        rect(-hw + 7, -hh + 31, hw - 7, hh - 26, fill=roof, outline=dark)
        if style == "sport":
            rect(-5, -hh + 32, 5, hh - 27, fill="#ffffff", outline="")
        elif style == "muscle":
            for sx in (-10, 4):
                rect(sx, -hh + 32, sx + 6, hh - 27, fill="#212121", outline="")
        elif style == "police":
            on = (self.frame // 8) % 2 == 0
            rect(-hw + 9, -4, 0, 3, fill="#ff1744" if on else "#7f0000", outline=dark)
            rect(0, -4, hw - 9, 3, fill="#7f7fff" if not on else "#0d1b7f", outline=dark)
        poly([-hw + 7, hh - 25, hw - 7, hh - 25, hw - 9, hh - 16, -hw + 9, hh - 16],
             fill=glass2, outline=dark)

        rect(-hw + 5, -hh + 2, -hw + 13, -hh + 7, fill="#fff59d", outline="")
        rect(hw - 13, -hh + 2, hw - 5, -hh + 7, fill="#fff59d", outline="")
        rect(-hw + 5, hh - 6, -hw + 13, hh - 2, fill="#ff1744", outline="")
        rect(hw - 13, hh - 6, hw - 5, hh - 2, fill="#ff1744", outline="")
        if style == "sport":
            rect(-hw + 2, hh - 4, hw - 2, hh + 1, fill="#212121", outline="")           # สปอยเลอร์

    def draw_hud(self):
        c = self.cv
        c.create_rectangle(0, 0, W, 42, fill="#111", outline="")
        c.create_text(12, 21, anchor="w", text=f"คะแนน: {self.score}",
                      fill="#ffffff", font=(FONT, 14, "bold"))
        c.create_text(W / 2 + 10, 21, text=f"{int(self.speed * 18)} km/h",
                      fill="#ff7043" if self.boosting else "#4fc3f7", font=(FONT, 14, "bold"))
        c.create_text(W - 12, 21, anchor="e", text=f"สูงสุด: {self.best}",
                      fill="#ffd54f", font=(FONT, 14, "bold"))
        frac = min(1.0, self.speed / 30)
        c.create_rectangle(0, 42, W, 46, fill="#222", outline="")
        c.create_rectangle(0, 42, W * frac, 46,
                           fill="#ff5252" if frac > 0.75 else "#69f0ae", outline="")

        # หลอดไนโตร (ขอบซ้าย)
        x0, x1, y0, y1 = 18, 40, 470, 690
        c.create_rectangle(x0 - 3, y0 - 3, x1 + 3, y1 + 3, fill="#111", outline="#000")
        fill_top = y1 - (y1 - y0) * self.nitro / NITRO_MAX
        c.create_rectangle(x0, fill_top, x1, y1, fill="#ff7043" if self.boosting else "#ff5722",
                           outline="")
        c.create_text((x0 + x1) / 2, y0 - 14, text="N2O", fill="#ffffff", font=(FONT, 9, "bold"))

        # หลอดโล่ (ขอบขวา)
        if self.shield > 0:
            x0, x1 = W - 40, W - 18
            c.create_rectangle(x0 - 3, y0 - 3, x1 + 3, y1 + 3, fill="#111", outline="#000")
            fill_top = y1 - (y1 - y0) * self.shield / SHIELD_FRAMES
            c.create_rectangle(x0, fill_top, x1, y1, fill="#40c4ff", outline="")
            c.create_text((x0 + x1) / 2, y0 - 14, text="โล่", fill="#ffffff", font=(FONT, 9, "bold"))

    def dim(self):
        self.cv.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")

    def overlay(self, title, sub, title_color="#ffffff"):
        c = self.cv
        self.dim()
        c.create_text(W / 2, H / 2 - 40, text=title, fill=title_color, font=(FONT, 34, "bold"))
        c.create_text(W / 2, H / 2 + 20, text=sub, fill="#dddddd", font=(FONT, 14))

    def draw_select(self):
        c = self.cv
        c.create_rectangle(0, 0, W, H, fill="#15181d", outline="")
        car = CARS[self.sel]
        blink = (self.frame // 20) % 2 == 0

        c.create_text(W / 2 + 3, 43, text="เกมรถแข่ง", fill="#000", font=(FONT, 30, "bold"))
        c.create_text(W / 2, 40, text="เกมรถแข่ง", fill="#ff5252", font=(FONT, 30, "bold"))
        c.create_text(W / 2, 82, text="เลือกรถของคุณ", fill="#ffd54f", font=(FONT, 16, "bold"))

        # พรีวิวรถ
        x0, y0, x1, y1 = PREVIEW_BOX
        c.create_rectangle(x0, y0, x1, y1, fill="#263238", outline="#ffd54f", width=3)
        c.create_rectangle(x0 + 100, y0, x1 - 100, y1, fill="#424242", outline="")
        for yy in range(y0 - 60, y1, 60):   # เส้นถนนวิ่งในพรีวิว
            ty = max(y0, yy + self.dash_off)
            by = min(y1, yy + self.dash_off + 30)
            if by > ty:
                c.create_rectangle(x0 + 97, ty, x0 + 101, by, fill="#eeeeee", outline="")
                c.create_rectangle(x1 - 101, ty, x1 - 97, by, fill="#eeeeee", outline="")
        bob = 3 * math.sin(self.frame * 0.08)
        self.draw_car(W / 2, (y0 + y1) / 2 + bob, car, scale=2.2)
        arrow_col = "#ffffff" if blink else "#9e9e9e"
        c.create_text(x0 - 35, (y0 + y1) / 2, text="◀", fill=arrow_col, font=(FONT, 26, "bold"))
        c.create_text(x1 + 35, (y0 + y1) / 2, text="▶", fill=arrow_col, font=(FONT, 26, "bold"))

        c.create_text(W / 2, 372, text=car["name"], fill=car["color"], font=(FONT, 22, "bold"))
        c.create_text(W / 2, 400, text=car["en"], fill="#bdbdbd", font=(FONT, 11, "bold"))
        c.create_text(W / 2, 426, text=car["desc"], fill="#ffffff", font=(FONT, 13))

        # ค่าพลัง
        for i, (key, label) in enumerate(STAT_LABELS):
            yy = 462 + i * 28
            c.create_text(90, yy, anchor="w", text=label, fill="#ffffff", font=(FONT, 12))
            for j in range(5):
                bx = 230 + j * 34
                fill = "#69f0ae" if j < car[key] else "#37474f"
                c.create_rectangle(bx, yy - 7, bx + 28, yy + 7, fill=fill, outline="#000")
        c.create_text(W / 2, 574, text=f"สถิติของรถคันนี้: {self.car_best(car)}",
                      fill="#ffd54f", font=(FONT, 12))

        # รูปย่อรถทุกคัน
        slot = W / len(CARS)
        for i, cr in enumerate(CARS):
            cx = slot * i + slot / 2
            if i == self.sel:
                c.create_rectangle(cx - 40, THUMB_Y - 38, cx + 40, THUMB_Y + 38,
                                   fill="#455a64", outline="#ffd54f", width=3)
            self.draw_car(cx, THUMB_Y, cr, scale=0.65)

        if blink:
            c.create_text(W / 2, 688, text="กด SPACE เพื่อเริ่มแข่ง",
                          fill="#69f0ae", font=(FONT, 17, "bold"))
        c.create_text(W / 2, 711, text="← → เลือกรถ   |   คลิกที่รถเพื่อเลือก / คลิกพรีวิวเพื่อเริ่ม",
                      fill="#cfd8dc", font=(FONT, 10))

    def draw_countdown(self):
        c = self.cv
        self.dim()
        n = math.ceil(self.count_t / 60)
        size = 70 + (self.count_t % 60)
        c.create_text(W / 2 + 4, 224, text=str(n), fill="#000", font=(FONT, size, "bold"))
        c.create_text(W / 2, 220, text=str(n), fill="#ffd54f", font=(FONT, size, "bold"))
        lines = [
            ("←  →  /  A  D", "เลี้ยว"),
            ("↑  /  W", "เร่งความเร็ว"),
            ("↓  /  S", "เบรก"),
            ("Shift  /  Space", "ไนโตร"),
            ("P", "หยุดชั่วคราว"),
        ]
        for i, (k, desc) in enumerate(lines):
            yy = 360 + i * 32
            c.create_text(W / 2 - 15, yy, anchor="e", text=k, fill="#ffffff", font=(FONT, 13, "bold"))
            c.create_text(W / 2 + 15, yy, anchor="w", text=desc, fill="#dddddd", font=(FONT, 13))
        c.create_text(W / 2, 545, text="$ = +50   N = ไนโตร   S = โล่กันชน   แซงเฉียด = +25",
                      fill="#ffeb3b", font=(FONT, 11))

    def draw_game_over(self):
        c = self.cv
        self.dim()
        c.create_text(W / 2, 180, text="ชนแล้ว!", fill="#ff5252", font=(FONT, 46, "bold"))
        c.create_text(W / 2, 255, text=f"คะแนน: {self.score}", fill="#ffffff", font=(FONT, 24, "bold"))
        stats = [
            f"รถ: {self.car['name']}",
            f"ระยะทาง: {self.distance / 1000:.2f} km",
            f"เหรียญ: {self.coins_got}   แซง: {self.passed} คัน   เฉียด: {self.near_misses}",
            f"สถิติของรถคันนี้: {self.car_best(self.car)}",
        ]
        for i, s in enumerate(stats):
            c.create_text(W / 2, 305 + i * 32, text=s, fill="#dddddd", font=(FONT, 14))
        if self.new_record:
            c.create_text(W / 2, 450, text="สถิติใหม่!", fill="#ffd54f", font=(FONT, 22, "bold"))
        if (self.frame // 20) % 2 == 0:
            c.create_text(W / 2, 520, text="กด SPACE เพื่อเล่นใหม่", fill="#69f0ae",
                          font=(FONT, 18, "bold"))
        c.create_text(W / 2, 560, text="กด C เพื่อเปลี่ยนรถ", fill="#ffffff", font=(FONT, 14))


def main():
    root = tk.Tk()
    RacingGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
