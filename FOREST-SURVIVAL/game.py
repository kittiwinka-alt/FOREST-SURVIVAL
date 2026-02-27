"""
game.py — คลาส Game หลัก: loop, events, update, draw
"""
import math
import random
import os
import sys
import json
import copy
import time
import pygame

from config import (
    SW, SH, TILE, FPS, SAVE, PROGRESS,
    PAL, WEAPON_DATA, ITEM_COLS, ITEM_NAMES, RECIPES, DIFFS, STAGES,
    SKIN_COLS, HAIR_COLS, SHIRT_COLS, PANTS_COLS,
    TGRASS, TWATER, TDEEP, TMUD, TROCK, TSAND,
)
from audio import Audio
from world import World, _precompute_tiles, get_tile_surf
from entities import PS, Enemy, Player
from renderer import (
    draw_tree, draw_bush, draw_ore, draw_mushroom, draw_reed,
    draw_flower, draw_campfire, draw_shelter, draw_torch,
    draw_house, draw_farm_plot
)
from ui import (
    draw_title, draw_customize, draw_stage_select,
    draw_stage_clear, draw_game_clear, draw_pause,
    draw_settings, draw_gameover, draw_hud,
    draw_inventory, draw_craft, draw_mission_panel, day_night
)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SW,SH))
        pygame.display.set_caption("🌲 Forest Survival v3")
        self.clock = pygame.time.Clock()

        # Fonts — try system fonts that render Thai
        def make_font(size, bold=False):
            for fn in ["Tahoma","FreeSansBold","DejaVu Sans","Arial","calibri",None]:
                try: return pygame.font.SysFont(fn, size, bold=bold)
                except: pass
            return pygame.font.Font(None, size)

        self.fonts = (make_font(22), make_font(44,True), make_font(16))

        _precompute_tiles()    # fill tile cache once — eliminates per-frame random
        self.audio = Audio()
        self.ps    = PS()

        # Pre-allocate reusable surfaces (ไม่ต้องสร้างใหม่ทุกเฟรม)
        self._night_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self._glow_cache = {}   # rng → Surface
        self._overlay_surf = pygame.Surface((SW, SH), pygame.SRCALPHA)

        # State machine
        self.state = "title"
        self.player  = None
        self.world   = None
        self.enemies = []
        self.cam_x = 0.0; self.cam_y = 0.0

        # Title inputs
        self.inp = ""; self.inp_on = True

        # Customize
        self.cos = {"skin":SKIN_COLS[0],"hair":HAIR_COLS[0],
                    "shirt":SHIRT_COLS[0],"pants":PANTS_COLS[0],
                    "hat":"none","weapon":"fists"}
        self.diff_idx = 1

        # In-game UI
        self.show_inv    = False
        self.show_craft  = False
        self.show_set    = False
        self.paused      = False
        self.inv_scroll  = 0
        self.craft_scroll= 0

        self.notifs      = []   # [msg, remaining, total]
        self.frame       = 0
        self.spawn_cd    = 5.0

        # ── Stage / Mission system ──
        self.cur_stage_id    = 1          # stage player is on
        self.done_stages     = []         # completed stage IDs
        self.mstats          = {}         # mission key → progress counter
        self.stage_clear_on  = False      # showing stage-clear screen
        self._sc_btns        = (pygame.Rect(0,0,1,1), pygame.Rect(0,0,1,1))
        self.show_stage_sel  = False      # showing stage select screen
        self._ss_data        = ([], pygame.Rect(0,0,1,1))  # (btns, back_btn)
        self.game_clear_on   = False

        # โหลด progress (done_stages) จากไฟล์ถ้ามี
        self._load_progress()
        self._gc_btn         = pygame.Rect(0,0,1,1)
        self.stage_intro_t   = 0.0       # seconds left for intro banner

        # Safe placeholder rects
        R = pygame.Rect(0,0,1,1)
        self._t  = (R,R,R,R,R,R)          # title btns
        self._go = (R,R,R)                 # gameover btns
        self._pa = {k:R for k in ["resume","stages","settings","menu"]}
        self._cr = (None, R)               # craft
        self._iv = ([], R)                 # inventory
        self._se = (R,R,R,R,R)             # settings: bgm_btn,bgm_slr,sfx_btn,sfx_slr,close
        self._cu = ({}, [], R, R)          # customize
        self.running = True

    # ── Notify ──
    def note(self, msg, dur=2.5):
        # ป้องกัน spam notification เดิมซ้ำๆ
        if self.notifs and self.notifs[-1][0] == msg:
            self.notifs[-1][1] = dur; return
        self.notifs.append([msg, dur, dur])
        if len(self.notifs) > 5:
            self.notifs = self.notifs[-5:]

    def diff(self):
        return DIFFS[self.diff_idx]

    # ── New game ──
    def _get_stage(self, sid=None):
        sid = sid or self.cur_stage_id
        for s in STAGES:
            if s["id"] == sid: return s
        return STAGES[0]

    def new_game(self, name, seed=None):
        try:
            stage = self._get_stage()
            world_seed = (seed or random.randint(1, 99999)) + stage["seed_off"]
            self.world = World(world_seed)
            # หาจุด spawn ที่เดินได้ใกล้กลางแผนที่
            _cx, _cy = self.world.W//2, self.world.H//2
            cx, cy = _cx*TILE, _cy*TILE
            found = False
            for r in range(0, max(self.world.W, self.world.H)):
                for dx in range(-r, r+1):
                    for dy in range(-r, r+1):
                        if r == 0 or abs(dx) == r or abs(dy) == r:
                            tx, ty = _cx+dx, _cy+dy
                            if self.world.walkable(tx, ty):
                                cx, cy = tx*TILE, ty*TILE
                                found = True
                                break
                    if found: break
                if found: break
            d = self.diff()
            # Apply stage difficulty multipliers on top of player diff
            import copy; ds = copy.copy(d)
            ds = dict(d); ds["nm"] = d["nm"] * stage["nm_mult"]; ds["em"] = d["em"] * stage["em_mult"]
            ds["ec"] = stage["ec"]
            self.player = Player(
                name or "นักผจญภัย", cx, cy,
                tuple(self.cos["skin"]), tuple(self.cos["hair"]),
                tuple(self.cos["shirt"]), tuple(self.cos["pants"]),
                self.cos["hat"], self.cos["weapon"], ds
            )
            self.enemies = []; self.ps = PS()
            self.show_inv=False; self.show_craft=False
            self.show_set=False; self.paused=False
            self.notifs=[]; self.spawn_cd=5.0
            self.cam_x=cx-SW//2; self.cam_y=cy-SH//2
            # Init mission stats
            self.mstats = {m["key"]: 0 for m in stage["missions"]}
            self.stage_clear_on = False
            self.game_clear_on  = False
            self.stage_intro_t  = 5.0
            self._spawn_enemies()
            self.state = "game"
            for msg in stage["intro"]:
                self.note(msg, 4.0)
        except Exception as e:
            print(f"[new_game error] {e}")
            import traceback; traceback.print_exc()
            self.state = "title"

    def _start_stage(self, sid, keep_player=True):
        """Transition to a new stage, optionally keeping player stats."""
        self.cur_stage_id = sid
        self._save_progress()   # บันทึกด่านที่กำลังเล่นทันที
        if keep_player and self.player:
            name = self.player.name
        else:
            name = self.inp.strip() or "นักผจญภัย"
        # Keep player alive but teleport to new world
        old_p = self.player
        self.new_game(name)
        if keep_player and old_p:
            self.player.level   = old_p.level
            self.player.xp      = old_p.xp
            self.player.xp_next = old_p.xp_next
            self.player.mhp     = old_p.mhp
            self.player.hp      = old_p.mhp   # full heal on new stage
            self.player.kills   = old_p.kills
            self.player.crafted = old_p.crafted
            self.player.survived= old_p.survived
            # Keep inventory
            self.player.inv     = dict(old_p.inv)
            self.player.weapon  = old_p.weapon
            self.player.armor   = old_p.armor
            self.player.poison_stacks = old_p.poison_stacks
            self.player.arrows  = old_p.arrows

    def _load_progress(self):
        """โหลด done_stages และ cur_stage_id จากไฟล์ progress"""
        try:
            if os.path.exists(PROGRESS):
                with open(PROGRESS,"r",encoding="utf-8") as f:
                    data = json.load(f)
                self.done_stages  = data.get("done_stages", [])
                self.cur_stage_id = data.get("cur_stage_id", 1)
        except Exception as e:
            print(f"[progress load] {e}")

    def _save_progress(self):
        """บันทึก done_stages และ cur_stage_id ลงไฟล์ progress"""
        try:
            with open(PROGRESS,"w",encoding="utf-8") as f:
                json.dump({
                    "done_stages":  self.done_stages,
                    "cur_stage_id": self.cur_stage_id,
                }, f, ensure_ascii=False)
        except Exception as e:
            print(f"[progress save] {e}")

    def load_game(self):
        if not os.path.exists(SAVE):
            self.note("ไม่พบไฟล์เซฟ"); return
        try:
            with open(SAVE,"r",encoding="utf-8") as f:
                data = json.load(f)
            pd = data["player"]
            did = pd.get("diff_id","normal")
            d = next((x for x in DIFFS if x["id"]==did), DIFFS[1])
            self.world = World(data["world_seed"])
            p = Player(
                pd["name"], pd.get("x",0), pd.get("y",0),
                tuple(pd.get("skin",list(SKIN_COLS[0]))),
                tuple(pd.get("hair",list(HAIR_COLS[0]))),
                tuple(pd.get("shirt",list(SHIRT_COLS[0]))),
                tuple(pd.get("pants",list(PANTS_COLS[0]))),
                pd.get("hat","none"), pd.get("weapon","fists"), d
            )
            # Restore all saved fields safely
            for k,v in pd.items():
                if k in ("skin","hair","shirt","pants"):
                    setattr(p, k, tuple(v))
                elif hasattr(p, k):
                    setattr(p, k, v)
            p.campfires=[tuple(x) for x in pd.get("campfires",[])]
            p.shelters =[tuple(x) for x in pd.get("shelters",[])]
            p.traps    =[tuple(x) for x in pd.get("traps",[])]
            p.torches  =[tuple(x) for x in pd.get("torches",[])]
            p.houses   =[tuple(x) for x in pd.get("houses",[])]
            raw_fp = pd.get("farm_plots",{})
            p.farm_plots = {eval(k):v for k,v in raw_fp.items()}
            p.diff = d
            self.player = p
            self.enemies=[]; self.ps=PS()
            self.show_inv=False; self.show_craft=False
            self.show_set=False; self.paused=False
            self.notifs=[]; self.spawn_cd=5.0
            self._spawn_enemies()
            self.state="game"
            self.note(f"โหลดสำเร็จ! ยินดีต้อนรับกลับ {p.name}!")
        except Exception as e:
            print(f"[load error] {e}")
            self.note(f"โหลดล้มเหลว: {e}")

    def save_game(self):
        if not self.player or not self.world: return
        try:
            with open(SAVE,"w",encoding="utf-8") as f:
                json.dump({
                    "player": self.player.save(),
                    "world_seed": self.world.seed,
                    "done_stages": self.done_stages,
                    "cur_stage_id": self.cur_stage_id,
                }, f, ensure_ascii=False)
            self.note("บันทึกแล้ว!")
        except Exception as e:
            self.note(f"บันทึกล้มเหลว: {e}")

    # ── Enemy spawn ──
    def _spawn_enemies(self):
        if not self.player or not self.world: return
        d = self.player.diff; target = d["ec"]; dm = d["em"]
        stage = self._get_stage()
        pool    = stage["pool"]
        weights = stage["weights"]
        t = self.player.gtime % 10
        night = t > 6
        # Night adds demons to any stage
        if night and "demon" not in pool:
            pool = pool + ["demon"]; weights = weights + [2]
        attempts = 0
        while len(self.enemies) < target and attempts < target*8:
            attempts += 1
            angle = random.uniform(0, math.pi*2)
            dist  = random.uniform(310,640)
            px = self.player.x + math.cos(angle)*dist
            py = self.player.y + math.sin(angle)*dist
            tx, ty = int(px//TILE), int(py//TILE)
            if not self.world.walkable(tx, ty): continue
            etype = random.choices(pool, weights=weights)[0]
            self.enemies.append(Enemy(etype, px, py, dm))

    # ── Attack ──
    def do_attack(self):
        p = self.player
        if not p or p.dead or p.atk_cd > 0: return
        p.atk_cd = p.atk_cd_max()
        p.is_swinging = True; p.atk_anim = 0
        self.audio.play("swing")

        hit = False
        rng = p.atk_rng()
        for e in self.enemies[:]:
            d = math.hypot(p.x-e.x, p.y-e.y)
            if d >= rng: continue
            dmg = p.atk_dmg()
            if p.poison_stacks > 0:
                e.poison += 3; p.poison_stacks -= 1; dmg = int(dmg*1.25)
            e.hp -= dmg; e.flash = 0.28
            if d > 1: kb=7; e.kbx=(e.x-p.x)/d*kb; e.kby=(e.y-p.y)/d*kb
            if not hit:  # เล่นเสียงและ blood ครั้งเดียวต่อ swing
                self.ps.blood(e.x, e.y, 5)
                self.audio.play("hit")
            hit = True
            p.combo = min(12, p.combo+1); p.combo_t = 2.2
            if e.hp <= 0:
                self._kill_enemy(e)
        if not hit:
            self._chop_mine()

    def _kill_enemy(self, e):
        p = self.player
        lv = p.gain_xp(e.xp); p.kills += 1
        # Mission stat: total kills
        self.mstats["kills"] = self.mstats.get("kills", 0) + 1
        # Demon kills
        if e.etype == "demon":
            self.mstats["demon_kills"] = self.mstats.get("demon_kills", 0) + 1
        for iid,qty in e.drop.items():
            tx,ty = int(e.x//TILE), int(e.y//TILE)
            self.world.add_drop(tx, ty, {"id":iid,"qty":qty})
        if e in self.enemies: self.enemies.remove(e)
        self.ps.emit(e.x, e.y, PAL["ui_gold"], 10, 80, 0.8, 6, True)
        self.note(f"⚔ ฆ่า {e.name}! +{e.xp}XP")
        if lv:
            self.note(f"🎉 เลเวลอัพ! Lv.{p.level}!")
            self.audio.play("levelup")
            self.ps.heal(p.x, p.y)
        self._check_missions()

    def _chop_mine(self):
        p = self.player
        tx, ty = int(p.x//TILE), int(p.y//TILE)
        for cc in [(tx,ty),(tx+1,ty),(tx-1,ty),(tx,ty+1),(tx,ty-1)]:
            obj = self.world.objs.get(cc)
            if not obj: continue
            power = 2 if p.weapon in ("axe","pickaxe") else 1
            drops = self.world.hit(cc[0], cc[1], power)
            for dr in drops:
                p.give(dr["id"], dr["qty"])
                self.note(f"✅ ได้ {ITEM_NAMES.get(dr['id'],dr['id'])} ×{dr['qty']}")
                self.audio.play("pickup")
                # Track mission stats for resources
                if dr["id"] == "wood":
                    self.mstats["wood_got"] = self.mstats.get("wood_got",0) + dr["qty"]
                elif dr["id"] == "stone":
                    self.mstats["stone_got"] = self.mstats.get("stone_got",0) + dr["qty"]
                elif dr["id"] == "herb":
                    self.mstats["herb_got"] = self.mstats.get("herb_got",0) + dr["qty"]
            self.ps.emit(cc[0]*TILE+TILE//2, cc[1]*TILE+TILE//2,
                         PAL["tree_trunk"], 5, 40, 0.4, 4, True)
            self._check_missions()
            return

    def place_item(self):
        p = self.player; px, py = p.x, p.y
        for iid, lst, msg in [
            ("campfire", p.campfires, "🔥 วางกองไฟ!"),
            ("shelter",  p.shelters,  "🏕 สร้างที่พัก!"),
            ("trap",     p.traps,     "🪤 วางกับดัก!"),
            ("torch",    p.torches,   "🕯 วางคบเพลิง!"),
            ("house",    p.houses,    "🏠 สร้างบ้าน!"),
        ]:
            if p.take(iid):
                lst.append((px,py)); self.note(msg); self.audio.play("click")
                if iid == "campfire":
                    self.mstats["camp_placed"] = self.mstats.get("camp_placed",0) + 1
                    self._check_missions()
                return
        # Farm plot: place as dict key
        if p.take("farm_plot"):
            p.farm_plots[(px,py)] = {"crop":None,"stage":0,"water":50,"fertilized":False}
            self.note("🌱 วางแปลงผัก!"); self.audio.play("click"); return
        self.note("❓ ต้องการ campfire / shelter / trap / torch / house / farm_plot")

    # ── Farming actions ──
    def do_farm_action(self):
        p = self.player; px, py = p.x, p.y
        # 1. Harvest if ready
        crop, qty = p.harvest_plot(px, py)
        if crop:
            self.note(f"🥕 เก็บเกี่ยว {ITEM_NAMES.get(crop,crop)} ×{qty}!")
            self.audio.play("pickup"); self.ps.heal(px, py); return
        # 2. Water if has can
        if p.inv.get("watering_can",0):
            if p.water_plot(px, py, self.world):
                self.note("💧 รดน้ำแปลงผักแล้ว!"); self.audio.play("drink"); return
        # 3. Apply fertilizer
        if p.inv.get("fertilizer",0):
            for pos, plot in p.farm_plots.items():
                fx,fy = pos
                if math.hypot(px-fx,py-fy) < TILE*1.5 and plot["crop"] and not plot["fertilized"]:
                    if p.take("fertilizer"):
                        plot["fertilized"] = True
                        self.note("🌿 ใส่ปุ๋ยแล้ว! เติบโตเร็วขึ้น 2x"); return
        # 4. Plant seed (cycle: carrot→potato→cabbage)
        if p.inv.get("veggie_seed",0):
            crops = ["carrot","potato","cabbage"]
            crop_name = crops[self.frame // 1 % 3]   # cycle through crops
            # pick based on what frame we're on for variety
            import time; idx = int(time.time()) % 3
            crop_name = crops[idx]
            result = p.plant_seed(px, py, crop_name)
            if result:
                self.note(f"🌱 ปลูก {ITEM_NAMES.get(result,result)}!"); self.audio.play("click"); return
        self.note("🌾 กด V ใกล้แปลง: ปลูก/รดน้ำ/เก็บเกี่ยว")

    # ── Main loop — fixed timestep + smooth render ──
    def run(self):
        import time
        prev_time = time.perf_counter()

        while self.running:
            now = time.perf_counter()
            dt  = min(now - prev_time, 0.05)   # cap at 50ms — ป้องกัน dt พุ่ง
            prev_time = now

            try:
                self._events()
            except Exception as e:
                import traceback; traceback.print_exc()

            try:
                self._update(dt)
            except Exception as e:
                import traceback; traceback.print_exc()

            try:
                self._draw()
            except Exception as e:
                import traceback; traceback.print_exc()

            self.frame += 1
            self.clock.tick_busy_loop(FPS)

        pygame.quit(); sys.exit()

    # ── Events ──
    def _events(self):
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False; return

            # ─ TITLE ─
            if self.state == "title":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self.audio.play("click")
                    bnew,bcust,bquit,ir = self._t
                    self.inp_on = ir.collidepoint(mouse)
                    if bnew.collidepoint(mouse) and self.inp.strip():
                        self.new_game(self.inp.strip())
                    elif bcust.collidepoint(mouse): self.state="customize"
                    elif bquit.collidepoint(mouse): self.running=False
                elif ev.type == pygame.KEYDOWN:
                    if self.inp_on:
                        if ev.key==pygame.K_BACKSPACE: self.inp=self.inp[:-1]
                        elif ev.key==pygame.K_RETURN and self.inp.strip():
                            self.new_game(self.inp.strip())
                        elif len(self.inp)<20: self.inp+=ev.unicode

            # ─ CUSTOMIZE ─
            elif self.state == "customize":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    swatches,dbts,bok,bback = self._cu
                    for key,sw in swatches.items():
                        for rect,opt in sw:
                            if rect.collidepoint(mouse):
                                self.cos[key]=opt
                    for i,dr in enumerate(dbts):
                        if dr.collidepoint(mouse): self.diff_idx=i
                    if bok.collidepoint(mouse):   self.state="stage_select"
                    if bback.collidepoint(mouse):  self.state="title"

            # ─ GAME OVER ─
            elif self.state == "gameover":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self.audio.play("click")
                    bret, bmenu, bcust = self._go
                    pname = self.player.name if self.player else "นักผจญภัย"
                    if bret.collidepoint(mouse):
                        self.new_game(pname)
                    elif bmenu.collidepoint(mouse):
                        self.state = "title"
                    elif bcust.collidepoint(mouse):
                        self.state = "customize"

            # ─ STAGE SELECT ─
            elif self.state == "stage_select":
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self.audio.play("click")
                    btns, bback = self._ss_data
                    if bback.collidepoint(mouse):
                        self.state = "title" if not self.player else "game"
                    for r, sid, locked in btns:
                        if r.collidepoint(mouse) and not locked:
                            self.cur_stage_id = sid
                            if self.player:
                                self._start_stage(sid, keep_player=True)
                            else:
                                self.new_game(self.inp.strip() or "นักผจญภัย")

            # ─ GAME ─
            elif self.state == "game":
                # Stage clear screen click
                if self.stage_clear_on or self.game_clear_on:
                    if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        self.audio.play("click")
                        if self.game_clear_on:
                            gc_btn = self._gc_btn
                            if gc_btn.collidepoint(mouse):
                                self.state = "title"
                        else:
                            bn, bs = self._sc_btns
                            next_id = self.cur_stage_id + 1
                            if bn.collidepoint(mouse):
                                if next_id <= len(STAGES):
                                    self._start_stage(next_id, keep_player=True)
                                else:
                                    # All stages complete!
                                    self.stage_clear_on = False
                                    self.game_clear_on  = True
                            elif bs.collidepoint(mouse):
                                self.stage_clear_on = False
                                self.state = "stage_select"
                    continue  # block other game input while clear screen shown

                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        if self.show_inv or self.show_craft or self.show_set:
                            self.show_inv=self.show_craft=self.show_set=False
                        else:
                            self.paused = not self.paused
                    elif ev.key == pygame.K_p and not (self.show_inv or self.show_craft or self.show_set):
                        self.paused = not self.paused
                    elif not self.paused:
                        if ev.key == pygame.K_i: self.show_inv=not self.show_inv; self.show_craft=False
                        elif ev.key == pygame.K_c: self.show_craft=not self.show_craft; self.show_inv=False
                        elif ev.key == pygame.K_m:
                            # Toggle stage select
                            self.state = "stage_select"
                        elif ev.key == pygame.K_SPACE: self.do_attack()
                        elif ev.key == pygame.K_e: self._chop_mine()
                        elif ev.key == pygame.K_f:
                            for fd in ["meat","fruit","mushroom","berry","herb"]:
                                if self.player.inv.get(fd,0)>0 and self.player.eat_item(fd):
                                    self.note(f"🍖 กิน {ITEM_NAMES.get(fd,fd)}"); self.audio.play("eat"); break
                        elif ev.key == pygame.K_g:
                            if self.player.drink(self.world): self.note("💧 ดื่มน้ำ!"); self.audio.play("drink")
                            else: self.note("ไม่มีแหล่งน้ำใกล้ๆ")
                        elif ev.key == pygame.K_b: self.place_item()
                        elif ev.key == pygame.K_v: self.do_farm_action()
                        elif ev.key == pygame.K_F5: self.save_game()

                elif ev.type == pygame.MOUSEMOTION:
                    if self.show_set and pygame.mouse.get_pressed()[0]:
                        mp2 = pygame.mouse.get_pos()
                        bgm_btn2,bgm_slr2,sfx_btn2,sfx_slr2,cb2 = self._se
                        if bgm_slr2.collidepoint(mp2):
                            ratio = (mp2[0]-bgm_slr2.x)/bgm_slr2.width
                            self.audio.set_bgm_vol(max(0.0,min(1.0,ratio)))
                        elif sfx_slr2.collidepoint(mp2):
                            ratio = (mp2[0]-sfx_slr2.x)/sfx_slr2.width
                            self.audio.set_sfx_vol(max(0.0,min(1.0,ratio)))

                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    mp = pygame.mouse.get_pos()
                    self.audio.play("click")

                    if self.paused:
                        bs = self._pa
                        if bs["resume"].collidepoint(mp):   self.paused=False
                        elif bs.get("stages") and bs["stages"].collidepoint(mp):
                            self.paused=False; self.state="stage_select"
                        elif bs["settings"].collidepoint(mp):self.show_set=True; self.paused=False
                        elif bs["menu"].collidepoint(mp):    self.state="title"; self.paused=False

                    elif self.show_set:
                        bgm_btn,bgm_slr,sfx_btn,sfx_slr,cb = self._se
                        if bgm_btn.collidepoint(mp):
                            self.audio.toggle_bgm()
                        elif sfx_btn.collidepoint(mp):
                            self.audio.toggle_sfx()
                        elif bgm_slr.collidepoint(mp):
                            ratio = (mp[0]-bgm_slr.x)/bgm_slr.width
                            self.audio.set_bgm_vol(max(0.0,min(1.0,ratio)))
                        elif sfx_slr.collidepoint(mp):
                            ratio = (mp[0]-sfx_slr.x)/sfx_slr.width
                            self.audio.set_sfx_vol(max(0.0,min(1.0,ratio)))
                        elif cb.collidepoint(mp): self.show_set=False

                    elif self.show_craft:
                        ci, cb = self._cr
                        if ci is not None:
                            r = RECIPES[ci]
                            if self.player.has(r["needs"]):
                                for k,v in r["needs"].items(): self.player.take(k,v)
                                self.player.give(r["id"],r["qty"])
                                self.player.crafted += 1
                                self.note(f"⚒ คราฟต์ {r['name']}!")
                                self.audio.play("craft")
                                # Mission tracking
                                self.mstats["crafted"] = self.mstats.get("crafted",0) + 1
                                if r["id"] in ("armor","iron_armor"):
                                    self.mstats["armor_made"] = self.mstats.get("armor_made",0) + 1
                                if r["id"] == "iron_sword":
                                    self.mstats["sword_made"] = self.mstats.get("sword_made",0) + 1
                                self._check_missions()
                                if self.player.gain_xp(12):
                                    self.note(f"🎉 เลเวลอัพ! Lv.{self.player.level}!")
                                    self.audio.play("levelup")
                        if cb.collidepoint(mp): self.show_craft=False
                        if ev.button==4: self.craft_scroll=max(0,self.craft_scroll-1)
                        elif ev.button==5: self.craft_scroll=min(len(RECIPES)-1,self.craft_scroll+1)

                    elif self.show_inv:
                        items, cb = self._iv
                        if cb.collidepoint(mp): self.show_inv=False
                        else:
                            ow=680; oh=500; ox=SW//2-ow//2; oy=SH//2-oh//2
                            cols=5; cs=108; rs=86
                            sx_=ox+(ow-cols*cs)//2; sy_=oy+52
                            for idx,(iid,qty) in enumerate(items):
                                c,r2=idx%cols,idx//cols-self.inv_scroll
                                if r2<0 or r2>=4: continue
                                rx=sx_+c*cs; ry=sy_+r2*rs
                                if pygame.Rect(rx,ry,cs-6,rs-6).collidepoint(mp):
                                    result = self.player.use_item(iid)
                                    if result == "heal":
                                        self.note("💊 ใช้ผ้าพัน +30HP"); self.audio.play("drink")
                                        self.ps.heal(self.player.x, self.player.y)
                                    elif result == "equip":
                                        self.note(f"🗡 สวม {ITEM_NAMES.get(iid,iid)}")
                                        self.audio.play("pickup")
                                    elif result == "poison":
                                        self.note("☠ ทายาพิษบนอาวุธ!")
                                    elif self.player.eat_item(iid):
                                        self.note(f"🍖 กิน {ITEM_NAMES.get(iid,iid)}")
                                        self.audio.play("eat")
                        if ev.button==4: self.inv_scroll=max(0,self.inv_scroll-1)
                        elif ev.button==5: self.inv_scroll+=1

                    elif ev.button==1:
                        self.do_attack()

    # ── Mission check ──
    def _check_missions(self):
        stage = self._get_stage()
        ms = stage["missions"]
        # Sync survived days
        if self.player:
            self.mstats["survived"] = self.player.survived
        all_done = all(self.mstats.get(m["key"],0) >= m["goal"] for m in ms)
        if all_done and not self.stage_clear_on and not self.game_clear_on:
            self.stage_clear_on = True
            self.audio.play("levelup")
            # Give rewards
            for m in ms:
                if self.player.gain_xp(m["rxp"]):
                    self.note(f"🎉 เลเวลอัพ! Lv.{self.player.level}!")
                for k,v in m.get("ritem",{}).items():
                    self.player.give(k,v)
            if self.cur_stage_id not in self.done_stages:
                self.done_stages.append(self.cur_stage_id)
                self._save_progress()   # บันทึกทันทีเมื่อผ่านด่าน

    # ── Update ──
    def _update(self, dt):
        if self.state != "game" or self.paused: return
        # Allow stage-clear screen clicks but no gameplay
        if self.stage_clear_on or self.game_clear_on: return
        if self.show_inv or self.show_craft or self.show_set: return

        p = self.player
        if p is None: return

        # Stage intro countdown
        if self.stage_intro_t > 0:
            self.stage_intro_t = max(0, self.stage_intro_t - dt)

        keys = pygame.key.get_pressed()
        prev_survived = p.survived
        p.update(keys, self.world, dt, self.ps)

        # Farm plot growth
        p.update_farm_plots(dt)

        if p.dead:
            self.state = "gameover"
            self.audio.play("death")
            return

        # Track survived days
        if p.survived > prev_survived:
            self.mstats["survived"] = p.survived
            self._check_missions()

        if p.moving and self.frame%22==0:
            # Surface-aware footstep
            tx_s, ty_s = int(p.x//TILE), int(p.y//TILE)
            tile_t = self.world.tiles[ty_s][tx_s] if 0<=ty_s<self.world.H and 0<=tx_s<self.world.W else TGRASS
            if tile_t == TROCK:   snd = "step_stone"
            elif tile_t in (TMUD, TSAND): snd = "step_dirt"
            else:                  snd = "step_grass"
            self.audio.play(snd)

        # Smooth camera — lerp ที่ใช้ dt จริง ไม่กระตุก
        tcx = max(0, min(p.x-SW//2, self.world.W*TILE-SW))
        tcy = max(0, min(p.y-SH//2, self.world.H*TILE-SH))
        lerp = min(1.0, 8.0 * dt)
        self.cam_x += (tcx-self.cam_x)*lerp
        self.cam_y += (tcy-self.cam_y)*lerp

        # Enemy spawn
        self.spawn_cd -= dt
        if self.spawn_cd <= 0:
            self.spawn_cd = 10.0; self._spawn_enemies()

        # Enemy update
        for e in self.enemies[:]:
            if e not in self.enemies: continue
            res = e.update(p.x, p.y, self.world, dt)
            if res == "dead":
                self._kill_enemy(e)
            elif res == "attack":
                if p.hit_cd <= 0:
                    dmg = max(0, e.atk - p.armor)
                    p.hp = max(0, p.hp - dmg)
                    p.flash = 0.4
                    p.hit_cd = 0.5   # invincible 0.5 วินาทีหลังโดนตี
                    self.ps.blood(p.x, p.y, 6)
                    self.audio.play("hit")
                    self.note(f"💢 {e.name} โจมตี! -{dmg}HP")
                    if p.hp <= 0:
                        p.dead = True; self.state="gameover"; self.audio.play("death"); return
            # Clean up dead
            if e in self.enemies and e.hp <= 0:
                self._kill_enemy(e)

        # Cull distant enemies
        self.enemies = [e for e in self.enemies
                        if math.hypot(e.x-p.x, e.y-p.y) < 1400]

        self.ps.update(dt)
        self.notifs = [[m,t-dt,mt] for m,t,mt in self.notifs if t>0]

        # Periodic warnings
        if p.hunger < 20 and self.frame%320==0: self.note("หิวมาก!")
        if p.thirst < 20 and self.frame%320==1: self.note("กระหายมาก!")

        # แจ้งเตือนใกล้กลางคืน — เตือนเมื่อ t≈5 (ช่วงพระอาทิตย์ตก)
        t_day = p.gtime % 10
        has_fire = bool(p.campfires) or bool(p.torches)
        if 4.8 < t_day < 5.2 and self.frame%60==0:
            if not has_fire:
                self.note("ใกล้กลางคืนแล้ว! รีบก่อไฟด่วน!")
            else:
                self.note("ใกล้กลางคืน — มีไฟแล้ว ปลอดภัย")

    # ── Draw ──
    def _draw(self):
        try:
            self._draw_inner()
        except Exception as e:
            print(f"[draw error] {e}")
            import traceback; traceback.print_exc()

    def _draw_inner(self):
        surf  = self.screen
        mouse = pygame.mouse.get_pos()
        F,Fm,Fs = self.fonts

        surf.fill(PAL["ui_bg"])

        # ─ TITLE ─
        if self.state == "title":
            self._t = draw_title(surf, self.fonts, mouse,
                                  self.inp, self.inp_on, self.frame)

        # ─ CUSTOMIZE ─
        elif self.state == "customize":
            self._cu = draw_customize(surf, self.fonts, mouse,
                                       self.cos, self.diff_idx, self.frame)

        # ─ STAGE SELECT ─
        elif self.state == "stage_select":
            self._ss_data = draw_stage_select(surf, self.fonts, mouse,
                                               self.cur_stage_id, self.done_stages)

        # ─ GAME OVER ─
        elif self.state == "gameover":
            result = draw_gameover(surf, self.fonts, self.player, mouse, self.frame)
            if result and len(result)==3: self._go = result

        # ─ GAME ─
        elif self.state == "game":
            cx, cy = int(self.cam_x), int(self.cam_y)

            # Tiles
            sx0=max(0,cx//TILE); sy0=max(0,cy//TILE)
            sx1=min(self.world.W,sx0+SW//TILE+2); sy1=min(self.world.H,sy0+SH//TILE+2)
            for ty in range(sy0,sy1):
                for tx in range(sx0,sx1):
                    t = self.world.tiles[ty][tx]
                    s = get_tile_surf(t, tx, ty)
                    surf.blit(s, (tx*TILE-cx, ty*TILE-cy))

            # World objects (draw only on-screen)
            for (tx,ty),obj in self.world.objs.items():
                px=tx*TILE-cx+TILE//2; py=ty*TILE-cy+TILE//2
                if not (-80<px<SW+80 and -100<py<SH+80): continue
                t = obj["type"]
                if   t=="tree":     draw_tree(surf,px,py,obj.get("stage",3))
                elif t=="ore":      draw_ore(surf,px,py,obj.get("stage",2))
                elif t=="bush":     draw_bush(surf,px,py)
                elif t=="mushroom": draw_mushroom(surf,px,py)
                elif t=="reed":     draw_reed(surf,px,py)
                elif t=="flower":   draw_flower(surf,px,py)

            # Placed structures
            p = self.player
            for (fx,fy) in p.campfires:
                sx,sy=int(fx-cx),int(fy-cy)
                if -30<sx<SW+30 and -30<sy<SH+30:
                    draw_campfire(surf,sx,sy,self.ps)
            for (sx2,sy2) in p.shelters:
                sx,sy=int(sx2-cx),int(sy2-cy)
                if -30<sx<SW+30 and -30<sy<SH+30:
                    draw_shelter(surf,sx,sy)
            for (tx2,ty2) in p.traps:
                sx,sy=int(tx2-cx),int(ty2-cy)
                if 0<sx<SW and 0<sy<SH:
                    pygame.draw.rect(surf,(80,55,22),(sx-7,sy-3,14,6))
                    for dx in[-9,9]: pygame.draw.line(surf,PAL["tree_trunk"],(sx,sy),(sx+dx,sy-10),2)
            for (tx2,ty2) in p.torches:
                sx,sy=int(tx2-cx),int(ty2-cy)
                if 0<sx<SW and 0<sy<SH:
                    draw_torch(surf,sx,sy,self.ps)

            # Houses
            for (hx2,hy2) in p.houses:
                sx,sy=int(hx2-cx),int(hy2-cy)
                if -60<sx<SW+60 and -60<sy<SH+60:
                    draw_house(surf,sx,sy)

            # Farm plots
            for (fpx,fpy),plot in p.farm_plots.items():
                sx,sy=int(fpx-cx),int(fpy-cy)
                if -50<sx<SW+50 and -50<sy<SH+50:
                    draw_farm_plot(surf,sx,sy,plot,self.frame)

            # Drops on ground
            for (tx,ty),items in self.world.drops.items():
                px=tx*TILE-cx+TILE//2; py=ty*TILE-cy+TILE//2
                if 0<px<SW and 0<py<SH:
                    for i,it in enumerate(items):
                        col=ITEM_COLS.get(it["id"],(150,150,150))
                        pygame.draw.circle(surf,col,(px+i*7,py),6)
                        pygame.draw.circle(surf,(220,215,205),(px+i*7,py),6,1)

            # Particles
            self.ps.draw(surf, cx, cy)

            # Enemies
            for e in self.enemies: e.draw(surf,cx,cy)

            # Attack range flash
            if p.is_swinging:
                rng = p.atk_rng()
                px_s,py_s=int(p.x-cx),int(p.y-cy)
                a=int(60*(1-p.atk_anim))
                if rng not in self._glow_cache:
                    g = pygame.Surface((rng*2,rng*2),pygame.SRCALPHA)
                    self._glow_cache[rng] = g
                glow = self._glow_cache[rng]
                glow.fill((0,0,0,0))
                pygame.draw.circle(glow,(255,220,60,a),(rng,rng),rng)
                surf.blit(glow,(px_s-rng,py_s-rng),special_flags=pygame.BLEND_ADD)

            # Player
            p.draw(surf, cx, cy, Fs)

            # Day/night
            day_night(surf, p, self._night_surf)

            # HUD
            draw_hud(surf, p, self.fonts, self.ps)

            # Day/Night progress bar
            t_cycle = p.gtime % 10
            is_day = t_cycle < 5
            day_pct = int((t_cycle / 5) * 100) if is_day else int(((t_cycle - 5) / 5) * 100)
            bar_w = 160; bar_h = 14
            bar_x = SW//2 - bar_w//2; bar_y = SH - 28
            pygame.draw.rect(surf, (20,20,35), (bar_x, bar_y, bar_w, bar_h), border_radius=7)
            fill_w = int(bar_w * day_pct / 100)
            bar_col = (220,190,60) if is_day else (60,80,160)
            if fill_w > 0:
                pygame.draw.rect(surf, bar_col, (bar_x, bar_y, fill_w, bar_h), border_radius=7)
            pygame.draw.rect(surf, PAL["ui_border"], (bar_x, bar_y, bar_w, bar_h), 1, border_radius=7)
            phase_lbl = f"กลางวัน {day_pct}%" if is_day else f"กลางคืน {day_pct}%"
            has_fire = bool(p.campfires) or bool(p.torches)
            if not is_day and not has_fire:
                phase_lbl += "  ก่อไฟด่วน!"
                phase_col = (230, 80, 80)
            else:
                phase_col = (220,190,60) if is_day else (120,150,220)
            pl = Fs.render(phase_lbl, True, phase_col)
            surf.blit(pl, (SW//2 - pl.get_width()//2, bar_y - 16))

            # Stage progress indicator (top center, compact)
            stage = self._get_stage()
            done_cnt = sum(1 for m in stage["missions"] if self.mstats.get(m["key"],0) >= m["goal"])
            total_cnt = len(stage["missions"])
            si_txt = f"ด่าน {self.cur_stage_id}/6  ●  ภารกิจ {done_cnt}/{total_cnt}"
            si = Fs.render(si_txt, True, PAL["ui_gold"] if done_cnt < total_cnt else (80,230,80))
            _si_bg = pygame.Surface((si.get_width()+20, si.get_height()+8))
            _si_bg.set_alpha(190); _si_bg.fill((12,22,10))
            surf.blit(_si_bg, (SW//2 - _si_bg.get_width()//2, 8))
            surf.blit(si, (SW//2 - si.get_width()//2, 12))

            # M key hint
            mk = Fs.render("M=เลือกด่าน", True, PAL["ui_dim"])
            surf.blit(mk, (SW//2 - mk.get_width()//2, 36))

            # Mission panel (right side)
            draw_mission_panel(surf, self.fonts, stage, self.mstats)

            # Stage intro banner
            if self.stage_intro_t > 0:
                alpha2 = min(255, int(self.stage_intro_t / 1.0 * 255))
                self._overlay_surf.fill((0,0,0,0))
                for li, line in enumerate(stage["intro"]):
                    font2 = Fm if li == 0 else F
                    ti = font2.render(line, True, PAL["ui_gold"])
                    _ts = pygame.Surface((ti.get_width()+30, ti.get_height()+12))
                    _ts.set_alpha(min(210, alpha2)); _ts.fill((8,20,8))
                    surf.blit(_ts, (SW//2 - _ts.get_width()//2, SH//2 - 60 + li*58))
                    surf.blit(ti,  (SW//2 - ti.get_width()//2,  SH//2 - 54 + li*58))

            # Combo text
            if p.combo >= 2:
                ct = F.render(f"COMBO ×{p.combo}", True, PAL["orange"])
                surf.blit(ct, (SW//2-ct.get_width()//2, SH//2-75))

            # Notifications (stacked, fade)
            for i,(msg,rem,tot) in enumerate(self.notifs[-4:]):
                alpha = min(255, int(rem/tot*255*2.5))
                t = Fs.render(msg, True, PAL["ui_gold"])
                _nb = pygame.Surface((t.get_width()+20, t.get_height()+8))
                _nb.set_alpha(min(200,alpha)); _nb.fill((12,22,10))
                surf.blit(_nb, (SW//2-_nb.get_width()//2, SH//2-130+i*30))
                surf.blit(t,   (SW//2-t.get_width()//2,   SH//2-126+i*30))

            # Stage clear overlay
            if self.stage_clear_on:
                next_id = self.cur_stage_id + 1
                bn, bs = draw_stage_clear(surf, self.fonts, mouse,
                                           stage, self.mstats, next_id <= len(STAGES))
                self._sc_btns = (bn, bs)

            # Game clear overlay
            elif self.game_clear_on:
                gc_btn = draw_game_clear(surf, self.fonts, mouse, self.player)
                self._gc_btn = gc_btn

            # Overlays
            elif self.paused:
                self._pa = draw_pause(surf, self.fonts, mouse)
            if self.show_set:
                self._se = draw_settings(surf, self.fonts, self.audio, mouse)
            if self.show_craft:
                self._cr = draw_craft(surf, self.fonts, p, self.craft_scroll, mouse)
            if self.show_inv:
                self._iv = draw_inventory(surf, self.fonts, p, self.inv_scroll, mouse)

        # FPS
        fps = Fs.render(f"FPS {int(self.clock.get_fps())}", True, (50,60,48))
        surf.blit(fps, (SW-55, SH-18))

        pygame.display.flip()



