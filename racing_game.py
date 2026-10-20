"""
เกมรถแข่ง (Racing Game) - ใช้แค่ tkinter ไม่ต้องติดตั้ง library เพิ่ม
พัฒนาโดย Uncle Engineer

วิธีเล่น:
    ← / →  หรือ A / D   : เลี้ยวซ้าย / ขวา
    ↑ / W               : เร่งความเร็ว
    ↓ / S               : เบรก
    P                   : หยุดชั่วคราว
    Space / Enter       : เริ่มเกม / เล่นใหม่
    Esc                 : ออกจากเกม

หลบรถคันอื่น เก็บเหรียญทอง ยิ่งวิ่งเร็ว คะแนนยิ่งขึ้นเร็ว!
"""

import os
import random
import tkinter as tk

# ---------------- ค่าคงที่ ----------------
W, H = 480, 720
ROAD_L, ROAD_R = 60, 420
LANES = 4
LANE_W = (ROAD_R - ROAD_L) / LANES
CAR_W, CAR_H = 46, 86
FRAME_MS = 16
FONT = "Tahoma"
HS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "racing_highscore.txt")

ENEMY_COLORS = ["#1e88e5", "#43a047", "#fdd835", "#8e24aa", "#fb8c00",
                "#00acc1", "#f5f5f5", "#6d4c41", "#3949ab", "#ec407a"]


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

        self.best = self.load_best()
        self.state = "menu"   # menu, play, pause, crash, over
        self.reset()
        self.loop()

    # ---------------- คะแนนสูงสุด ----------------
    def load_best(self):
        try:
            with open(HS_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def save_best(self):
        try:
            with open(HS_FILE, "w", encoding="utf-8") as f:
                f.write(str(self.best))
        except OSError:
            pass

    # ---------------- เริ่มเกมใหม่ ----------------
    def reset(self):
        self.px = lane_center(1)
        self.py = H - 120
        self.speed = 6.0
        self.distance = 0.0
        self.coins_got = 0
        self.passed = 0
        self.enemies = []
        self.coins = []
        self.particles = []
        self.dash_off = 0.0
        self.spawn_cd = 60
        self.coin_cd = 90
        self.crash_timer = 0
        self.new_record = False
        # รถแต่ละเลนวิ่งความเร็วคงที่ (ไม่ชนกันเอง)
        self.lane_speed = [random.uniform(1.5, 4.5) for _ in range(LANES)]
        self.trees = []
        for _ in range(14):
            self.trees.append(self.make_tree(random.uniform(0, H)))

    def make_tree(self, y):
        if random.random() < 0.5:
            x = random.uniform(8, ROAD_L - 22)
        else:
            x = random.uniform(ROAD_R + 22, W - 8)
        return [x, y, random.uniform(12, 20)]

    @property
    def score(self):
        return int(self.distance / 10) + self.coins_got * 50 + self.passed * 5

    # ---------------- ปุ่มกด ----------------
    def on_press(self, e):
        k = e.keysym.lower()
        self.keys.add(k)
        if k == "escape":
            self.root.destroy()
        elif k in ("space", "return"):
            if self.state in ("menu", "over"):
                self.reset()
                self.state = "play"
        elif k == "p":
            if self.state == "play":
                self.state = "pause"
            elif self.state == "pause":
                self.state = "play"

    def on_release(self, e):
        self.keys.discard(e.keysym.lower())

    def held(self, *names):
        return any(n in self.keys for n in names)

    # ---------------- ลูปหลัก ----------------
    def loop(self):
        self.update()
        self.draw()
        self.root.after(FRAME_MS, self.loop)

    def update(self):
        if self.state == "play":
            self.update_play()
        elif self.state == "crash":
            self.update_particles()
            self.crash_timer -= 1
            if self.crash_timer <= 0:
                self.state = "over"
        elif self.state == "menu":
            # ฉากหลังวิ่งเบาๆ ตอนอยู่หน้าเมนู
            self.scroll_world(4)

    def update_play(self):
        # ความเร็ว: ยิ่งไกลยิ่งเร็วขึ้น
        min_spd = min(5 + self.distance / 5000, 12)
        max_spd = min(12 + self.distance / 3000, 22)
        if self.held("up", "w"):
            self.speed += 0.15
        elif self.held("down", "s"):
            self.speed -= 0.35
        else:
            self.speed -= 0.03
        self.speed = max(min_spd, min(max_spd, self.speed))

        # เลี้ยว
        steer = 4 + self.speed * 0.25
        if self.held("left", "a"):
            self.px -= steer
        if self.held("right", "d"):
            self.px += steer
        self.px = max(ROAD_L + CAR_W / 2 + 4, min(ROAD_R - CAR_W / 2 - 4, self.px))

        self.distance += self.speed
        self.scroll_world(self.speed)

        # รถศัตรู
        for en in self.enemies:
            en["y"] += self.speed - en["spd"]
        before = len(self.enemies)
        self.enemies = [en for en in self.enemies if en["y"] < H + CAR_H]
        self.passed += before - len(self.enemies)

        self.spawn_cd -= 1
        if self.spawn_cd <= 0:
            self.spawn_enemy()
            base = max(18, 55 - self.distance / 800)
            self.spawn_cd = int(random.uniform(base * 0.7, base * 1.3))

        # เหรียญ
        for c in self.coins:
            c["y"] += self.speed
        self.coins = [c for c in self.coins if c["y"] < H + 30]
        self.coin_cd -= 1
        if self.coin_cd <= 0:
            self.spawn_coin()
            self.coin_cd = random.randint(50, 120)

        # ชน
        pl, pt, pr, pb = self.player_box()
        for en in self.enemies:
            ex, ey = lane_center(en["lane"]), en["y"]
            if (pl < ex + CAR_W / 2 - 6 and pr > ex - CAR_W / 2 + 6 and
                    pt < ey + CAR_H / 2 - 6 and pb > ey - CAR_H / 2 + 6):
                self.crash()
                return

        remaining = []
        for c in self.coins:
            cx = lane_center(c["lane"])
            if pl - 12 < cx < pr + 12 and pt - 12 < c["y"] < pb + 12:
                self.coins_got += 1
                self.sparkle(cx, c["y"])
            else:
                remaining.append(c)
        self.coins = remaining
        self.update_particles()

    def scroll_world(self, spd):
        self.dash_off = (self.dash_off + spd) % 60
        for t in self.trees:
            t[1] += spd
            if t[1] > H + 30:
                t[:] = self.make_tree(random.uniform(-80, -20))

    def player_box(self):
        return (self.px - CAR_W / 2 + 4, self.py - CAR_H / 2 + 4,
                self.px + CAR_W / 2 - 4, self.py + CAR_H / 2 - 4)

    def spawn_enemy(self):
        # เลนที่มีรถอยู่ใกล้ด้านบน -> ห้ามเกิดซ้อน
        busy_top = {en["lane"] for en in self.enemies if en["y"] < CAR_H * 1.5}
        # ห้ามปิดทุกเลน ต้องเหลือทางหนีอย่างน้อย 1 เลน
        band = {en["lane"] for en in self.enemies if en["y"] < CAR_H * 3.5}
        free = [i for i in range(LANES) if i not in busy_top]
        random.shuffle(free)
        for lane in free:
            if len(band | {lane}) < LANES:
                self.enemies.append({
                    "lane": lane,
                    "y": -CAR_H,
                    "spd": self.lane_speed[lane],
                    "color": random.choice(ENEMY_COLORS),
                })
                return

    def spawn_coin(self):
        lane = random.randrange(LANES)
        for en in self.enemies:
            if en["lane"] == lane and en["y"] < CAR_H * 2:
                return
        self.coins.append({"lane": lane, "y": -20})

    def crash(self):
        self.state = "crash"
        self.crash_timer = 70
        for _ in range(60):
            self.particles.append([
                self.px, self.py - 20,
                random.uniform(-6, 6), random.uniform(-7, 3),
                random.randint(25, 60),
                random.choice(["#ff5722", "#ffc107", "#ff9800", "#f44336", "#555555"]),
            ])
        if self.score > self.best:
            self.best = self.score
            self.new_record = True
            self.save_best()

    def sparkle(self, x, y):
        for _ in range(12):
            self.particles.append([x, y, random.uniform(-3, 3), random.uniform(-3, 3),
                                   random.randint(10, 22), "#ffeb3b"])

    def update_particles(self):
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.15
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]

    # ---------------- วาด ----------------
    def draw(self):
        c = self.cv
        c.delete("all")

        # ต้นไม้ริมทาง
        for x, y, s in self.trees:
            c.create_oval(x - s + 4, y - s + 6, x + s + 4, y + s + 6, fill="#2a6a2a", outline="")
            c.create_oval(x - s, y - s, x + s, y + s, fill="#1f7a1f", outline="#145214")
            c.create_oval(x - s / 2, y - s / 2 - 3, x + s / 3, y + s / 4 - 3, fill="#2e9e2e", outline="")

        # ถนน
        c.create_rectangle(ROAD_L, 0, ROAD_R, H, fill="#444", outline="")
        # ขอบถนนแดง-ขาว
        off = self.dash_off
        for y in range(-60, H + 60, 30):
            yy = y + (off % 60)
            color = "#e53935" if (y // 30) % 2 == 0 else "#ffffff"
            c.create_rectangle(ROAD_L - 10, yy, ROAD_L, yy + 30, fill=color, outline="")
            c.create_rectangle(ROAD_R, yy, ROAD_R + 10, yy + 30, fill=color, outline="")
        # เส้นแบ่งเลน
        for i in range(1, LANES):
            x = ROAD_L + LANE_W * i
            for y in range(-60, H + 60, 60):
                yy = y + off
                c.create_rectangle(x - 3, yy, x + 3, yy + 32, fill="#eeeeee", outline="")

        # เหรียญ
        for co in self.coins:
            x, y = lane_center(co["lane"]), co["y"]
            c.create_oval(x - 13, y - 13, x + 13, y + 13, fill="#ffc107", outline="#b28704", width=3)
            c.create_text(x, y, text="$", fill="#8d6e00", font=(FONT, 12, "bold"))

        # รถศัตรู
        for en in self.enemies:
            self.draw_car(lane_center(en["lane"]), en["y"], en["color"])

        # รถผู้เล่น
        if self.state != "crash" and self.state != "over":
            self.draw_car(self.px, self.py, "#e53935", player=True)
        elif self.state == "crash" and self.crash_timer > 50:
            self.draw_car(self.px, self.py, "#7a1f1f", player=True)

        # อนุภาค
        for x, y, _, _, life, col in self.particles:
            r = 2 + life / 12
            c.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="")

        self.draw_hud()

        if self.state == "menu":
            self.draw_menu()
        elif self.state == "pause":
            self.overlay("หยุดชั่วคราว", "กด P เพื่อเล่นต่อ")
        elif self.state == "over":
            self.draw_game_over()

    def draw_car(self, x, y, color, player=False):
        c = self.cv
        w, h = CAR_W, CAR_H
        l, t, r, b = x - w / 2, y - h / 2, x + w / 2, y + h / 2
        # เงา
        c.create_rectangle(l + 4, t + 6, r + 4, b + 6, fill="#333", outline="")
        # ล้อ
        for wy in (t + 12, b - 32):
            c.create_rectangle(l - 4, wy, l + 6, wy + 20, fill="#111", outline="")
            c.create_rectangle(r - 6, wy, r + 4, wy + 20, fill="#111", outline="")
        # ตัวรถ
        pts = [l + 8, t, r - 8, t, r, t + 14, r, b - 8, r - 6, b, l + 6, b, l, b - 8, l, t + 14]
        c.create_polygon(pts, fill=color, outline="#1a1a1a", width=2)
        # แถบลายรถแข่ง
        if player:
            c.create_rectangle(x - 5, t + 2, x + 5, b - 2, fill="#ffffff", outline="")
        # กระจกหน้า / หลังคา / กระจกหลัง
        c.create_polygon(l + 7, t + 30, r - 7, t + 30, r - 10, t + 20, l + 10, t + 20,
                         fill="#90caf9", outline="#1a1a1a")
        c.create_rectangle(l + 7, t + 31, r - 7, b - 26, fill=color, outline="#1a1a1a")
        if player:
            c.create_rectangle(x - 5, t + 32, x + 5, b - 27, fill="#ffffff", outline="")
        c.create_polygon(l + 7, b - 25, r - 7, b - 25, r - 9, b - 16, l + 9, b - 16,
                         fill="#64b5f6", outline="#1a1a1a")
        # ไฟหน้า / ไฟท้าย
        c.create_rectangle(l + 5, t + 2, l + 13, t + 7, fill="#fff59d", outline="")
        c.create_rectangle(r - 13, t + 2, r - 5, t + 7, fill="#fff59d", outline="")
        c.create_rectangle(l + 5, b - 6, l + 13, b - 2, fill="#ff1744", outline="")
        c.create_rectangle(r - 13, b - 6, r - 5, b - 2, fill="#ff1744", outline="")

    def draw_hud(self):
        c = self.cv
        c.create_rectangle(0, 0, W, 42, fill="#111", outline="")
        c.create_text(12, 21, anchor="w", text=f"คะแนน: {self.score}",
                      fill="#ffffff", font=(FONT, 14, "bold"))
        c.create_text(W / 2 + 10, 21, text=f"{int(self.speed * 18)} km/h",
                      fill="#4fc3f7", font=(FONT, 14, "bold"))
        c.create_text(W - 12, 21, anchor="e", text=f"สูงสุด: {self.best}",
                      fill="#ffd54f", font=(FONT, 14, "bold"))
        # เกจความเร็ว
        frac = min(1.0, self.speed / 22)
        c.create_rectangle(0, 42, W, 46, fill="#222", outline="")
        c.create_rectangle(0, 42, W * frac, 46,
                           fill="#ff5252" if frac > 0.75 else "#69f0ae", outline="")

    def overlay(self, title, sub, title_color="#ffffff"):
        c = self.cv
        c.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")
        c.create_text(W / 2, H / 2 - 40, text=title, fill=title_color, font=(FONT, 34, "bold"))
        c.create_text(W / 2, H / 2 + 20, text=sub, fill="#dddddd", font=(FONT, 15))

    def draw_menu(self):
        c = self.cv
        c.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")
        c.create_text(W / 2 + 3, 183, text="เกมรถแข่ง", fill="#000", font=(FONT, 48, "bold"))
        c.create_text(W / 2, 180, text="เกมรถแข่ง", fill="#ff5252", font=(FONT, 48, "bold"))
        c.create_text(W / 2, 240, text="RACING GAME", fill="#ffd54f", font=(FONT, 20, "bold"))
        lines = [
            "←  →  /  A  D     เลี้ยว",
            "↑  /  W              เร่งความเร็ว",
            "↓  /  S               เบรก",
            "P                       หยุดชั่วคราว",
            "Esc                    ออกจากเกม",
        ]
        for i, s in enumerate(lines):
            c.create_text(W / 2, 320 + i * 34, text=s, fill="#ffffff", font=(FONT, 14))
        c.create_text(W / 2, 520, text="หลบรถคันอื่น และเก็บเหรียญ $ (+50)",
                      fill="#ffeb3b", font=(FONT, 13))
        if (self.dash_off // 30) % 2 == 0:
            c.create_text(W / 2, 600, text="กด SPACE เพื่อเริ่มเกม",
                          fill="#69f0ae", font=(FONT, 18, "bold"))

    def draw_game_over(self):
        c = self.cv
        c.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")
        c.create_text(W / 2, 220, text="ชนแล้ว!", fill="#ff5252", font=(FONT, 46, "bold"))
        c.create_text(W / 2, 300, text=f"คะแนน: {self.score}", fill="#ffffff", font=(FONT, 24, "bold"))
        c.create_text(W / 2, 345, text=f"ระยะทาง: {self.distance / 1000:.2f} km   เหรียญ: {self.coins_got}",
                      fill="#dddddd", font=(FONT, 14))
        c.create_text(W / 2, 380, text=f"แซงรถไป: {self.passed} คัน",
                      fill="#dddddd", font=(FONT, 14))
        if self.new_record:
            c.create_text(W / 2, 430, text="สถิติใหม่!", fill="#ffd54f", font=(FONT, 22, "bold"))
        c.create_text(W / 2, 520, text="กด SPACE เพื่อเล่นใหม่", fill="#69f0ae",
                      font=(FONT, 18, "bold"))


def main():
    root = tk.Tk()
    RacingGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
