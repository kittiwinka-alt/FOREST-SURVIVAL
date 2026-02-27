"""
entities.py — PS (Particle System), Enemy, Player
"""
import math
import random
import pygame
from config import PAL, TILE, TWATER, TDEEP, SW, SH, WEAPON_DATA

class PS:   # Particle System
    __slots__ = ("p",)
    def __init__(self): self.p = []

    def add(self, x, y, vx, vy, col, life, sz=3, grav=0.04):
        self.p.append([float(x),float(y),float(vx),float(vy),col,float(life),float(life),sz,grav])

    def emit(self, x, y, col, n=6, spread=60, life=0.5, sz=4, up=False):
        for _ in range(n):
            a = random.uniform(0, math.pi*2)
            s = random.uniform(0.3,1.0)*spread/60
            vy = s*math.sin(a) - (random.uniform(0.5,1.5) if up else 0)
            self.p.append([float(x),float(y),s*math.cos(a),vy,col,
                           life*random.uniform(0.7,1.3),life*random.uniform(0.7,1.3),sz,0.04])

    def blood(self, x, y, n=8):
        for _ in range(n):
            a = random.uniform(0,math.pi*2)
            s = random.uniform(0.5,2.5)
            self.p.append([float(x),float(y),s*math.cos(a),s*math.sin(a)-0.5,
                           PAL["blood"],random.uniform(0.25,0.45),0.4,random.randint(2,5),0.06])

    def fire(self, x, y):
        if len(self.p) > 150: return   # ไม่เพิ่ม fire ถ้า particle เต็มแล้ว
        col = random.choice([PAL["orange"],(255,200,80),(220,80,20),(255,160,40)])
        vx = random.uniform(-0.3,0.3)
        vy = random.uniform(-1.4,-0.6)
        self.p.append([float(x+random.uniform(-4,4)),float(y+random.uniform(-2,2)),
                       vx,vy,col,random.uniform(0.25,0.5),0.45,random.randint(3,7),-0.04])

    def heal(self, x, y):
        for _ in range(5):
            self.add(x+random.uniform(-10,10), y+random.uniform(-10,10),
                     random.uniform(-0.2,0.2), random.uniform(-1.2,-0.4),
                     PAL["heal"], random.uniform(0.4,0.7), 4, -0.02)

    def update(self, dt):
        alive = []
        for p in self.p:
            p[0]+=p[2]*dt*60; p[1]+=p[3]*dt*60; p[3]+=p[8]*dt*60; p[5]-=dt
            if p[5]>0: alive.append(p)
        self.p = alive[-150:]  # cap at 150 particles

    def draw(self, surf, cx, cy):
        for p in self.p:
            sx, sy = int(p[0]-cx), int(p[1]-cy)
            if not (0<=sx<SW and 0<=sy<SH): continue
            a = max(0.0, p[5]/p[6])
            r,g,b = p[4]; sz = max(1, int(p[7]*a))
            pygame.draw.circle(surf, (int(r*a),int(g*a),int(b*a)), (sx,sy), sz)

# ─────────────────────────────────────────────────────
#  ENEMIES
# ─────────────────────────────────────────────────────
ETYPE = {
    "wolf":  {"name":"หมาป่า","hp":35, "atk":9,  "spd":2.4,"sz":20,"col":(75,80,110), "xp":28,"drop":{"meat":1}},
    "boar":  {"name":"หมูป่า","hp":50, "atk":13, "spd":1.9,"sz":25,"col":(130,88,55), "xp":38,"drop":{"meat":2}},
    "bear":  {"name":"หมี",   "hp":100,"atk":22, "spd":1.6,"sz":32,"col":(100,68,38), "xp":70,"drop":{"meat":3,"leather":1}},
    "snake": {"name":"งู",    "hp":18, "atk":16, "spd":2.8,"sz":14,"col":(55,140,45), "xp":22,"drop":{}},
    "bandit":{"name":"โจร",   "hp":60, "atk":16, "spd":2.0,"sz":22,"col":(125,78,55), "xp":50,"drop":{"iron":1}},
    "demon": {"name":"ปีศาจ", "hp":140,"atk":28, "spd":1.9,"sz":30,"col":(145,30,175),"xp":110,"drop":{"iron":2}},
}


class Enemy:
    _font = None

    def __init__(self, etype, x, y, diff_mult=1.0):
        d = ETYPE[etype]; self.etype = etype
        self.name = d["name"]
        self.hp   = int(d["hp"]*diff_mult); self.mhp = self.hp
        self.atk  = int(d["atk"]*diff_mult)
        self.spd  = d["spd"]; self.sz = d["sz"]
        self.col  = d["col"]; self.xp = d["xp"]
        self.drop = d["drop"]
        self.x = float(x); self.y = float(y)
        self.state = "patrol"; self.ptarget = (x,y)
        self.acd = 0; self.flash = 0; self.ang = 0
        self.kbx = 0.0; self.kby = 0.0
        self.poison = 0.0
        self.alert_r = 210; self.atk_r = 58
        self.anim = 0.0  # walk cycle

    def update(self, px, py, world, dt):
        self.acd  = max(0, self.acd-dt)
        self.flash= max(0, self.flash-dt)
        if self.poison > 0:
            self.poison -= dt; self.hp -= dt*6
            if self.hp <= 0: return "dead"
        # Knockback — ลด exponential แบบ frame-rate independent ไม่กระตุก
        if abs(self.kbx)>0.5 or abs(self.kby)>0.5:
            nx = self.x + self.kbx*dt*60; ny = self.y + self.kby*dt*60
            if world.walkable(int(nx//TILE), int(ny//TILE)):
                self.x, self.y = nx, ny
            damp = 0.75 ** (dt * 60)   # frame-rate independent damping
            self.kbx *= damp; self.kby *= damp
            return None

        dx, dy = px-self.x, py-self.y
        dist = math.hypot(dx,dy)
        if dist < self.alert_r: self.state = "chase"
        elif self.state=="chase" and dist > self.alert_r*1.6: self.state="patrol"

        spd = self.spd*60*dt
        if self.state == "chase":
            if dist > 5:
                self.ang = math.atan2(dy,dx)
                nx = self.x + (dx/dist)*spd; ny = self.y + (dy/dist)*spd
                if world.walkable(int(nx//TILE), int(ny//TILE)):
                    self.x, self.y = nx, ny
                    self.anim += dt*6
            if dist < self.atk_r and self.acd <= 0:
                self.acd = 1.6; return "attack"
        else:
            pdx, pdy = self.ptarget[0]-self.x, self.ptarget[1]-self.y
            pd = math.hypot(pdx,pdy)
            if pd < 8 or random.random()<0.007:
                self.ptarget = (self.x+random.uniform(-140,140), self.y+random.uniform(-140,140))
            elif pd > 0:
                self.ang = math.atan2(pdy,pdx)
                nx = self.x+(pdx/pd)*spd*0.5; ny = self.y+(pdy/pd)*spd*0.5
                if world.walkable(int(nx//TILE), int(ny//TILE)):
                    self.x, self.y = nx, ny
                    self.anim += dt*3
        return None

    def draw(self, surf, cx, cy):
        sx, sy = int(self.x-cx), int(self.y-cy)
        if not (-60<sx<SW+60 and -60<sy<SH+60): return

        # Shadow
        pygame.draw.ellipse(surf, PAL["shadow"], (sx-self.sz, sy+self.sz-6, self.sz*2, self.sz//2+4))

        # Body with walk bob
        bob = int(math.sin(self.anim*math.pi)*2)
        col = (255,90,90) if self.flash>0 else self.col
        if self.poison > 0: col = tuple(max(0,min(255,c+v)) for c,v in zip(col,(0,50,-20)))

        pygame.draw.circle(surf, col, (sx, sy-bob), self.sz)
        # Outline
        pygame.draw.circle(surf, tuple(max(0,c-40) for c in col), (sx, sy-bob), self.sz, 2)

        # Eyes follow direction
        ex = int(sx + self.sz*0.55*math.cos(self.ang))
        ey = int(sy - bob + self.sz*0.55*math.sin(self.ang))
        pygame.draw.circle(surf, (255,235,180), (ex,ey), 5)
        pygame.draw.circle(surf, (200,0,0),     (ex,ey), 3)

        # HP bar (only when damaged)
        if self.hp < self.mhp:
            bw = self.sz*2+4; bx = sx-self.sz-2; by = sy-self.sz-bob-14
            pygame.draw.rect(surf, (40,15,15), (bx,by,bw,6), border_radius=3)
            ratio = max(0, self.hp/self.mhp)
            bar_col = PAL["hp"] if ratio>0.4 else PAL["hp_low"]
            pygame.draw.rect(surf, bar_col, (bx,by,int(bw*ratio),6), border_radius=3)

        # Name label
        if not Enemy._font:
            Enemy._font = pygame.font.SysFont(None, 15)
        t = Enemy._font.render(self.name, True, (220,210,195))
        surf.blit(t, (sx-t.get_width()//2, sy-self.sz-bob-28))


# ─ Player cosmetic options ─
SKIN_COLS  = [(240,200,160),(210,168,128),(180,128,88),(120,78,48),(255,218,183),(198,138,98)]
HAIR_COLS  = [(50,28,8),(22,12,4),(200,165,75),(215,48,48),(48,48,195),(175,175,175),(238,238,238)]
SHIRT_COLS = [(35,100,35),(48,48,178),(175,48,48),(178,118,28),(98,28,118),(48,148,148),(58,58,58)]
PANTS_COLS = [(38,33,8),(18,18,78),(78,28,28),(98,68,18),(58,18,78),(28,98,98),(28,28,28)]
HATS = ["none","cap","helmet","crown","hood"]
START_WEPS = ["fists","stone_knife","wooden_spear","iron_sword"]

class Player:
    def __init__(self, name, x, y, skin, hair, shirt, pants, hat, weapon, diff):
        self.name = name
        self.x = float(x); self.y = float(y)
        self.skin = skin; self.hair = hair
        self.shirt = shirt; self.pants = pants; self.hat = hat
        self.weapon = weapon
        self.diff = diff

        hp0 = 50 if diff["id"]=="hell" else 100
        self.hp = hp0; self.mhp = hp0
        self.hunger = 100; self.thirst = 100; self.stamina = 100
        self.xp = 0; self.level = 1; self.xp_next = 100
        self.armor = 0

        self.inv = {}      # id → qty
        self.campfires = []; self.shelters = []; self.traps = []; self.torches = []
        self.houses = []      # [(x,y)]
        self.farm_plots = {}  # (x,y) -> {"crop":None,"stage":0,"water":0,"fertilized":False}

        self.day = 1; self.gtime = 0.0
        self.survived = 0; self.kills = 0; self.crafted = 0

        self.facing = 0.0
        self.walk_anim = 0.0; self.moving = False
        self.atk_cd = 0.0; self.atk_anim = 0.0; self.is_swinging = False
        self.flash = 0.0
        self.hit_cd = 0.0   # invincibility frames หลังโดนตี
        self.dead = False
        self.combo = 0; self.combo_t = 0.0
        self.poison_stacks = 0
        self.speed = 3.0
        self.step_cd = 0.0

        self.arrows = 5   # starting arrows

    # ── Inventory ──
    def give(self, iid, qty=1):
        self.inv[iid] = self.inv.get(iid,0) + qty
    def take(self, iid, qty=1):
        if self.inv.get(iid,0) >= qty:
            self.inv[iid] -= qty
            if self.inv[iid] == 0: del self.inv[iid]
            return True
        return False
    def has(self, needs):
        return all(self.inv.get(k,0)>=v for k,v in needs.items())

    def gain_xp(self, amt):
        self.xp += amt
        lv = False
        while self.xp >= self.xp_next:
            self.xp -= self.xp_next; self.level += 1
            self.xp_next = int(self.xp_next*1.45)
            self.mhp = min(200, self.mhp+12); self.hp = min(self.mhp, self.hp+30)
            lv = True
        return lv

    def atk_dmg(self):
        w = WEAPON_DATA.get(self.weapon, WEAPON_DATA["fists"])
        base = w["dmg"] + (self.level-1)*2
        if self.combo >= 3: base = int(base*1.5)
        return base

    def atk_rng(self):
        return WEAPON_DATA.get(self.weapon, WEAPON_DATA["fists"])["rng"]

    def atk_cd_max(self):
        return WEAPON_DATA.get(self.weapon, WEAPON_DATA["fists"])["cd"]

    # ── Update ──
    def update(self, keys, world, dt, ps):
        if self.dead: return

        self.gtime += dt/15   # 1 วันเกม ≈ 2.5 วินาทีจริง (เร็ว 4x ป้องกันเบื่อ)
        prev = self.day
        self.day = int(self.gtime/10) + 1
        if self.day > prev: self.survived += 1

        # Decay
        nm = self.diff["nm"] * dt
        near_fire     = any(math.hypot(self.x-fx, self.y-fy)<TILE*4.5 for fx,fy in self.campfires)
        near_shelter  = any(math.hypot(self.x-sx, self.y-sy)<TILE*3   for sx,sy in self.shelters)
        near_house    = any(math.hypot(self.x-hx, self.y-hy)<TILE*4   for hx,hy in self.houses)
        self.hunger = max(0, self.hunger - nm*0.35)
        self.thirst = max(0, self.thirst - nm*0.55)
        if near_fire or near_shelter or near_house: self.stamina = min(100, self.stamina + dt*2.2)
        else:                          self.stamina = max(0,   self.stamina - dt*0.12)
        if near_house:   self.hp = min(self.mhp, self.hp + dt*1.6)
        elif near_shelter: self.hp = min(self.mhp, self.hp + dt*0.8)
        if near_fire:    self.hp = min(self.mhp, self.hp + dt*0.3)
        if self.hunger <= 0: self.hp = max(0, self.hp - dt*0.6)
        if self.thirst <= 0: self.hp = max(0, self.hp - dt*1.0)
        if self.hp <= 0: self.dead = True; return

        # Timers
        self.flash   = max(0, self.flash-dt)
        self.hit_cd  = max(0, self.hit_cd-dt)
        self.atk_cd  = max(0, self.atk_cd-dt)
        self.combo_t = max(0, self.combo_t-dt)
        if self.combo_t <= 0: self.combo = 0
        if self.is_swinging:
            self.atk_anim = min(1, self.atk_anim+dt*9)
            if self.atk_anim >= 1: self.is_swinging=False; self.atk_anim=0

        # Movement
        dx = dy = 0
        run = keys[pygame.K_LSHIFT] and self.stamina > 8
        spd = self.speed * (1.65 if run else 1.0) * TILE * dt
        if run: self.stamina = max(0, self.stamina - dt*4.5)
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy=-1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy=1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx=-1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx=1
        self.moving = dx!=0 or dy!=0
        if self.moving:
            self.facing = math.atan2(dy,dx)
            n = math.hypot(dx,dy); dx/=n; dy/=n
            nx = self.x + dx*spd; ny = self.y + dy*spd
            if world.walkable(int(nx//TILE), int(self.y//TILE)): self.x = nx
            if world.walkable(int(self.x//TILE), int(ny//TILE)): self.y = ny
            self.walk_anim += dt*(10 if run else 6)
            self.step_cd -= dt
            if self.step_cd <= 0:
                self.step_cd = 0.28
                ps.emit(self.x, self.y+16, PAL["mud"], 3, 25, 0.2, 3)

        # Auto-pickup
        tx, ty = int(self.x//TILE), int(self.y//TILE)
        for c in [(tx,ty),(tx-1,ty),(tx+1,ty),(tx,ty-1),(tx,ty+1)]:
            for it in world.pop_drops(*c):
                self.give(it["id"], it["qty"])

        # Trap check
        for trap in self.traps[:]:
            if random.random() < 0.0008:
                if math.hypot(self.x-trap[0], self.y-trap[1]) < 6:
                    self.give("meat",1); self.traps.remove(trap)

    def update_farm_plots(self, dt):
        """Grow crops over time. Call every frame."""
        CROPS = {"carrot":{"time":40.0,"food":(35,5)},
                 "potato":{"time":55.0,"food":(50,8)},
                 "cabbage":{"time":35.0,"food":(28,6)}}
        for pos, plot in self.farm_plots.items():
            if plot["crop"] and plot["water"] > 0:
                speed = 2.0 if plot["fertilized"] else 1.0
                plot["stage"] = min(1.0, plot["stage"] + dt/CROPS[plot["crop"]]["time"] * speed)
                plot["water"] = max(0, plot["water"] - dt*0.008)

    def harvest_plot(self, px, py):
        """Harvest ready crop at nearby farm plot."""
        CROPS = {"carrot":{"time":40.0,"food":(35,5)},
                 "potato":{"time":55.0,"food":(50,8)},
                 "cabbage":{"time":35.0,"food":(28,6)}}
        for pos, plot in list(self.farm_plots.items()):
            fx, fy = pos
            if math.hypot(px-fx, py-fy) < TILE*1.5 and plot["crop"] and plot["stage"] >= 1.0:
                crop = plot["crop"]
                qty  = 2 if plot["fertilized"] else 1
                self.give(crop, qty)
                # Also add seed back sometimes
                if random.random() < 0.4: self.give("veggie_seed", 1)
                # Reset plot
                plot["crop"] = None; plot["stage"] = 0; plot["water"] = 0; plot["fertilized"] = False
                return crop, qty
        return None, 0

    def plant_seed(self, px, py, crop="carrot"):
        """Plant veggie seed in nearest empty farm plot."""
        for pos, plot in self.farm_plots.items():
            fx, fy = pos
            if math.hypot(px-fx, py-fy) < TILE*1.5 and plot["crop"] is None:
                if self.take("veggie_seed"):
                    plot["crop"]  = crop
                    plot["stage"] = 0
                    plot["water"] = 50
                    return crop
        return None

    def water_plot(self, px, py, world):
        """Water farm plots nearby using watering_can."""
        if not self.inv.get("watering_can", 0): return False
        watered = False
        for pos, plot in self.farm_plots.items():
            fx, fy = pos
            if math.hypot(px-fx, py-fy) < TILE*2:
                plot["water"] = min(100, plot["water"] + 60)
                watered = True
        return watered

    def drink(self, world):
        tx,ty = int(self.x//TILE), int(self.y//TILE)
        for cx,cy in [(tx,ty),(tx-1,ty),(tx+1,ty),(tx,ty-1),(tx,ty+1)]:
            if 0<=cy<world.H and 0<=cx<world.W and world.tiles[cy][cx] in (TWATER,TDEEP):
                self.thirst = min(100, self.thirst+50); return True
        return False

    def eat_item(self, iid):
        food = {"berry":(18,6),"mushroom":(22,0),"fruit":(28,12),"meat":(48,0),"herb":(10,8),"carrot":(32,8),"potato":(45,5),"cabbage":(28,10)}
        if iid in food and self.take(iid):
            h,t = food[iid]
            self.hunger = min(100, self.hunger+h)
            self.thirst = min(100, self.thirst+t)
            return True
        return False

    def use_item(self, iid):
        if iid=="bandage" and self.take("bandage"):
            self.hp = min(self.mhp, self.hp+30); return "heal"
        if iid=="armor"      and self.take("armor"):      self.armor=5;  return "equip"
        if iid=="iron_armor" and self.take("iron_armor"): self.armor=13; return "equip"
        if iid=="poison"     and self.take("poison"):     self.poison_stacks+=3; return "poison"
        if iid in WEAPON_DATA and self.inv.get(iid,0)>0:
            self.weapon=iid; return "equip"
        return None

    # ── Draw ──
    def draw(self, surf, cx, cy, font_s):
        sx = int(self.x-cx); sy = int(self.y-cy)
        bob = int(math.sin(self.walk_anim*math.pi)*3) if self.moving else 0
        skin = PAL["dmg_flash"] if self.flash>0 else self.skin

        # Shadow
        pygame.draw.ellipse(surf, PAL["shadow"], (sx-15, sy+17, 30, 10))

        # Legs with walk animation
        ls = int(math.sin(self.walk_anim*math.pi)*8) if self.moving else 0
        pygame.draw.line(surf, self.pants, (sx-5, sy+10-bob), (sx-5+ls, sy+26-bob), 7)
        pygame.draw.line(surf, self.pants, (sx+5, sy+10-bob), (sx+5-ls, sy+26-bob), 7)
        # Boots
        boot = tuple(max(0,c-40) for c in self.pants)
        pygame.draw.ellipse(surf, boot, (sx-8+ls-4, sy+23-bob, 12, 6))
        pygame.draw.ellipse(surf, boot, (sx+2-ls-4, sy+23-bob, 12, 6))

        # Torso
        pygame.draw.rect(surf, self.shirt, (sx-12, sy-8-bob, 24, 20), border_radius=4)
        # Shirt shading
        pygame.draw.rect(surf, tuple(max(0,c-30) for c in self.shirt), (sx-12, sy-8-bob, 5, 20), border_radius=2)

        # Arms
        sa = int(math.sin(self.walk_anim*math.pi)*10) if self.moving else 0
        swing = int(self.atk_anim*35) if self.is_swinging else 0
        # Left arm
        pygame.draw.line(surf, skin, (sx-12, sy-2-bob), (sx-20, sy+10-bob-sa), 5)
        # Right arm (holds weapon)
        pygame.draw.line(surf, skin, (sx+12, sy-2-bob), (sx+20, sy+10-bob+sa-swing), 5)

        # Weapon in right hand
        self._draw_weapon(surf, sx, sy, bob, swing)

        # Head
        pygame.draw.circle(surf, skin, (sx, sy-16-bob), 14)
        # Hair
        pygame.draw.arc(surf, self.hair, pygame.Rect(sx-14, sy-30-bob, 28, 20), 0, math.pi, 5)
        # Eyes
        ex = int(sx + 7*math.cos(self.facing))
        ey = int(sy-16-bob + 5*math.sin(self.facing))
        pygame.draw.circle(surf, (30,20,10), (ex,ey), 3)
        # Hat
        self._draw_hat(surf, sx, sy, bob)
        # Armor overlay
        if self.armor > 0:
            ac = (155,155,172) if self.armor>=13 else (88,88,95)
            pygame.draw.rect(surf, ac, (sx-13, sy-9-bob, 26, 22), 2, border_radius=3)
        # Poison glow
        if self.poison_stacks > 0:
            pygame.draw.circle(surf, (50,220,80), (sx+14, sy-24-bob), 5)
        # Name
        t = font_s.render(self.name, True, PAL["ui_gold"])
        surf.blit(t, (sx-t.get_width()//2, sy-40-bob))

    def _draw_weapon(self, surf, sx, sy, bob, swing):
        w = self.weapon; hx, hy = sx+20, sy+10-bob+swing
        if w == "fists": return
        elif w in ("stone_knife",):
            pygame.draw.line(surf, (140,140,148), (sx+15, sy+8-bob), (hx+2, hy-14), 3)
        elif w == "wooden_spear":
            pygame.draw.line(surf, (115,75,28), (sx+12, sy+6-bob), (sx+30, sy-14-bob+swing), 3)
            pygame.draw.polygon(surf, (140,140,148), [(sx+28,sy-16-bob+swing),(sx+34,sy-22-bob+swing),(sx+30,sy-10-bob+swing)])
        elif w == "iron_sword":
            pygame.draw.line(surf, (145,145,175), (sx+14, sy+8-bob), (hx-2, hy-16), 5)
            pygame.draw.line(surf, (100,65,25), (sx+10, sy+5-bob), (sx+18, sy+2-bob), 3)
        elif w == "axe":
            pygame.draw.line(surf, PAL["tree_trunk"], (sx+14, sy+8-bob), (hx, hy-12), 3)
            pygame.draw.polygon(surf, (140,140,148), [(hx-1,hy-12),(hx+7,hy-16),(hx+5,hy-5)])
        elif w == "club":
            pygame.draw.line(surf, (90,58,20), (sx+14, sy+8-bob), (hx+2, hy-8), 5)
            pygame.draw.circle(surf, PAL["tree_trunk"], (hx+2, hy-8), 8)
        elif w == "pickaxe":
            pygame.draw.line(surf, PAL["tree_trunk"], (sx+14, sy+8-bob), (hx, hy-10), 3)
            pygame.draw.line(surf, (140,140,148), (hx-4, hy-14), (hx+8, hy-7), 3)
        elif w == "bow":
            pygame.draw.arc(surf, PAL["tree_trunk"], pygame.Rect(sx+14, sy-8-bob, 14, 22), -0.8, 0.8, 3)
            pygame.draw.line(surf, (180,165,140), (sx+21, sy-8-bob), (sx+21, sy+14-bob), 1)

    def _draw_hat(self, surf, sx, sy, bob):
        hx, hy = sx, sy-30-bob
        if self.hat == "cap":
            pygame.draw.ellipse(surf, (30,90,30), (hx-16,hy+2,32,10))
            pygame.draw.rect(surf, (30,90,30), (hx-11,hy-8,22,12), border_radius=3)
        elif self.hat == "helmet":
            pygame.draw.arc(surf, (155,155,170), pygame.Rect(hx-15,hy-5,30,20), 0, math.pi, 11)
            pygame.draw.line(surf, (130,130,145), (hx-6,hy+2),(hx+6,hy+2), 3)
        elif self.hat == "crown":
            pts=[(hx-11,hy+2),(hx-9,hy-9),(hx-4,hy),(hx,hy-11),(hx+4,hy),(hx+9,hy-9),(hx+11,hy+2)]
            pygame.draw.polygon(surf, PAL["ui_gold"], pts)
            pygame.draw.polygon(surf, PAL["orange"], pts, 2)
        elif self.hat == "hood":
            pygame.draw.arc(surf, (38,38,78), pygame.Rect(hx-17,hy-6,34,22), 0, math.pi, 18)

    def save(self):
        return {
            "name":self.name,"x":self.x,"y":self.y,
            "hp":self.hp,"mhp":self.mhp,"hunger":self.hunger,
            "thirst":self.thirst,"stamina":self.stamina,
            "xp":self.xp,"level":self.level,"xp_next":self.xp_next,
            "inv":self.inv,"weapon":self.weapon,"armor":self.armor,
            "day":self.day,"gtime":self.gtime,
            "kills":self.kills,"crafted":self.crafted,"survived":self.survived,
            "skin":list(self.skin),"hair":list(self.hair),
            "shirt":list(self.shirt),"pants":list(self.pants),
            "hat":self.hat,"diff_id":self.diff["id"],
            "campfires":self.campfires,"shelters":self.shelters,
            "traps":self.traps,"torches":self.torches,
            "arrows":self.arrows,
            "houses":self.houses,
            "farm_plots":{str(k):v for k,v in self.farm_plots.items()},
        }
