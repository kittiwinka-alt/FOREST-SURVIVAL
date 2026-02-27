"""
ui.py — HUD, Screens, Overlays ทั้งหมด
"""
import math
import os
import pygame
from config import PAL, TILE, SW, SH, SAVE, WEAPON_DATA, ITEM_COLS, ITEM_NAMES, RECIPES, DIFFS, STAGES, SKIN_COLS, HAIR_COLS, SHIRT_COLS, PANTS_COLS, HATS, START_WEPS

def draw_mission_panel(surf, fonts, stage, mstats):
    F, Fm, Fs = fonts
    ms = stage["missions"]
    pw = 255; ph = 36 + len(ms) * 66
    px = SW - pw - 6; py = 8
    _panel(surf, px, py, pw, ph, 210)
    ht = Fs.render(f"ภารกิจ — {stage['name']}", True, PAL["ui_gold"])
    surf.blit(ht, (px + 8, py + 8))
    for i, m in enumerate(ms):
        my = py + 30 + i * 66
        val = mstats.get(m["key"], 0)
        done = val >= m["goal"]
        nc = (80, 220, 80) if done else PAL["ui_text"]
        nt = Fs.render(("✓ " if done else "- ") + m["name"], True, nc)
        surf.blit(nt, (px + 8, my))
        bw = pw - 18
        pygame.draw.rect(surf, (25, 35, 22), (px + 8, my + 18, bw, 10), border_radius=5)
        ratio = min(1.0, val / m["goal"])
        if ratio > 0:
            pc = (80, 210, 80) if done else PAL["xp"]
            pygame.draw.rect(surf, pc, (px + 8, my + 18, int(bw * ratio), 10), border_radius=5)
        pygame.draw.rect(surf, PAL["ui_border"], (px + 8, my + 18, bw, 10), 1, border_radius=5)
        pt = Fs.render(f"{int(val)}/{m['goal']}", True, PAL["ui_dim"])
        surf.blit(pt, (px + 8, my + 32))


# ─────────────────────────────────────────────────────
#  STAGE SELECT SCREEN
# ─────────────────────────────────────────────────────
def draw_stage_select(surf, fonts, mouse, cur_id, done_ids):
    F, Fm, Fs = fonts
    surf.fill((8, 14, 8))
    pygame.draw.rect(surf, (18, 30, 16), (0, 0, SW, 68))
    pygame.draw.line(surf, PAL["ui_border"], (0, 68), (SW, 68), 1)
    t = Fm.render("เลือกด่าน — Stage Select", True, PAL["ui_gold"])
    surf.blit(t, (SW // 2 - t.get_width() // 2, 14))

    btns = []
    cw = (SW - 50) // 3; ch = (SH - 120) // 2
    for i, s in enumerate(STAGES):
        col_i = i % 3; row_i = i // 3
        x = 20 + col_i * (cw + 5); y = 80 + row_i * (ch + 5)
        r = pygame.Rect(x, y, cw, ch - 5)
        done   = s["id"] in done_ids
        max_unlocked = max((max(done_ids) + 1) if done_ids else 1, cur_id)
        locked = s["id"] > max_unlocked
        active = s["id"] == cur_id
        hov    = r.collidepoint(mouse) and not locked

        bg = (10, 30, 10) if done else ((20, 35, 15) if active else ((12, 12, 12) if locked else (14, 22, 14)))
        pygame.draw.rect(surf, bg, r, border_radius=10)
        bc = (80, 220, 80) if done else (PAL["ui_gold"] if active else ((40, 40, 40) if locked else s["col"]))
        bw = 3 if (active or hov) else 1
        pygame.draw.rect(surf, bc, r, bw, border_radius=10)

        if locked:
            lt = F.render("ล็อก", True, (70, 70, 70))
            surf.blit(lt, (r.x + r.w // 2 - lt.get_width() // 2, r.y + r.h // 2 - 12))
        else:
            nt = F.render(s["name"], True, (80, 240, 80) if done else PAL["ui_gold"])
            surf.blit(nt, (r.x + 12, r.y + 10))
            st = Fs.render(s["subtitle"], True, PAL["ui_dim"])
            surf.blit(st, (r.x + 12, r.y + 36))
            dd = Fs.render(s["desc"], True, PAL["ui_text"])
            surf.blit(dd, (r.x + 12, r.y + 56))
            for mi, m in enumerate(s["missions"]):
                mc2 = (80, 200, 80) if done else PAL["ui_dim"]
                mt = Fs.render(f"  • {m['name']}", True, mc2)
                surf.blit(mt, (r.x + 12, r.y + 80 + mi * 20))
            if done:
                dk = Fs.render("ผ่านแล้ว", True, (80, 220, 80))
                surf.blit(dk, (r.x + r.w - dk.get_width() - 10, r.y + 10))
            if active:
                ck = Fs.render("กำลังเล่น", True, PAL["ui_gold"])
                surf.blit(ck, (r.x + r.w - ck.get_width() - 10, r.y + 10))

        btns.append((r, s["id"], locked))

    bback = pygame.Rect(SW // 2 - 80, SH - 48, 160, 36)
    _btn(surf, bback, "กลับ", F, bback.collidepoint(mouse))
    return btns, bback


# ─────────────────────────────────────────────────────
#  STAGE CLEAR SCREEN
# ─────────────────────────────────────────────────────
def draw_stage_clear(surf, fonts, mouse, stage, mstats, has_next):
    F, Fm, Fs = fonts
    ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
    ov.fill((0, 8, 0, 215)); surf.blit(ov, (0, 0))

    t = Fm.render("🏆  ด่านสำเร็จ!", True, PAL["ui_gold"])
    surf.blit(t, (SW // 2 - t.get_width() // 2, 90))
    sn = F.render(stage["name"], True, (120, 230, 100))
    surf.blit(sn, (SW // 2 - sn.get_width() // 2, 152))

    bw2 = 520; bh2 = 40 + len(stage["missions"]) * 44 + 44
    bx2 = SW // 2 - bw2 // 2; by2 = 195
    _panel(surf, bx2, by2, bw2, bh2, 230)

    total_xp = 0
    for i, m in enumerate(stage["missions"]):
        val = mstats.get(m["key"], 0)
        done2 = val >= m["goal"]
        mc = (80, 225, 80) if done2 else (200, 80, 80)
        mt = Fs.render(("✓ " if done2 else "✗ ") + m["name"] + f"  ({int(val)}/{m['goal']})", True, mc)
        surf.blit(mt, (bx2 + 18, by2 + 16 + i * 44))
        total_xp += m["rxp"]

    xt = F.render(f"EXP รางวัลรวม: +{total_xp}", True, PAL["xp"])
    surf.blit(xt, (SW // 2 - xt.get_width() // 2, by2 + bh2 - 36))

    bn = pygame.Rect(SW // 2 - 175, by2 + bh2 + 20, 165, 52)
    bs = pygame.Rect(SW // 2 + 10,  by2 + bh2 + 20, 165, 52)
    lbl = "ด่านถัดไป" if has_next else "จบเกม!"
    _btn(surf, bn, lbl, F, bn.collidepoint(mouse))
    _btn(surf, bs, "เลือกด่าน", F, bs.collidepoint(mouse))
    return bn, bs


# ─────────────────────────────────────────────────────
#  GAME CLEAR (all stages done)
# ─────────────────────────────────────────────────────
def draw_game_clear(surf, fonts, mouse, player):
    F, Fm, Fs = fonts
    surf.fill((4, 8, 4))
    t = Fm.render("คุณผ่านทุกด่าน!", True, PAL["ui_gold"])
    surf.blit(t, (SW // 2 - t.get_width() // 2, 110))
    sub = F.render("ยินดีด้วย! คุณเป็นผู้รอดชีวิตผู้ยิ่งใหญ่!", True, (120, 230, 100))
    surf.blit(sub, (SW // 2 - sub.get_width() // 2, 172))
    if player:
        stats = [
            ("เลเวล", f"Lv.{player.level}"),
            ("ฆ่าศัตรู", f"{player.kills} ตัว"),
            ("อยู่รอด", f"{player.survived} วัน"),
            ("คราฟต์", f"{player.crafted} ครั้ง"),
        ]
        _panel(surf, SW // 2 - 180, 220, 360, 40 + len(stats) * 38, 210)
        for i, (k, v) in enumerate(stats):
            kt = F.render(k, True, PAL["ui_dim"])
            vt = F.render(v, True, PAL["ui_text"])
            surf.blit(kt, (SW // 2 - 160, 238 + i * 38))
            surf.blit(vt, (SW // 2 + 20,  238 + i * 38))
    bm = pygame.Rect(SW // 2 - 85, SH - 100, 170, 52)
    _btn(surf, bm, "เมนูหลัก", F, bm.collidepoint(mouse))
    return bm


# ─────────────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────────────
def _panel(surf, x, y, w, h, alpha=200):
    s = pygame.Surface((w,h), pygame.SRCALPHA)
    s.fill((14,22,12,alpha)); surf.blit(s,(x,y))
    pygame.draw.rect(surf, PAL["ui_border"], (x,y,w,h), 1, border_radius=8)

def _btn(surf, rect, text, font, hover=False, disabled=False):
    if disabled:
        bc = (45,55,45); fc = PAL["ui_dim"]
    else:
        bc = PAL["ui_hover"] if hover else (38,62,34); fc = PAL["ui_gold"] if hover else PAL["ui_text"]
    bd = PAL["ui_gold"] if hover else PAL["ui_border"]
    pygame.draw.rect(surf, bc, rect, border_radius=7)
    pygame.draw.rect(surf, bd, rect, 2, border_radius=7)
    t = font.render(text, True, fc)
    surf.blit(t, (rect[0]+rect[2]//2-t.get_width()//2, rect[1]+rect[3]//2-t.get_height()//2))

def _bar(surf, x, y, w, h, val, mx, col, label, font):
    pygame.draw.rect(surf, (25,35,22), (x,y,w,h), border_radius=4)
    fw = max(0, int(w * min(1,val/max(1,mx))))
    if fw > 0:
        # Gradient-like effect: bright center
        pygame.draw.rect(surf, col, (x,y,fw,h), border_radius=4)
        if fw > 6:
            lighter = tuple(min(255,c+40) for c in col)
            pygame.draw.rect(surf, lighter, (x+2,y+1,fw-4,h//2-1), border_radius=2)
    pygame.draw.rect(surf, PAL["ui_border"], (x,y,w,h), 1, border_radius=4)
    t = font.render(f"{label} {int(val)}/{int(mx)}", True, PAL["ui_text"])
    surf.blit(t, (x+5, y+(h-t.get_height())//2))

def _swatch(surf, rect, col, selected):
    pygame.draw.rect(surf, col, rect, border_radius=5)
    bc = PAL["ui_gold"] if selected else (50,60,48)
    pygame.draw.rect(surf, bc, rect, 3 if selected else 1, border_radius=5)

# ─────────────────────────────────────────────────────
#  SCREENS
# ─────────────────────────────────────────────────────
def draw_title(surf, fonts, mouse, inp, inp_on, frame):
    F, Fm, Fs = fonts
    surf.fill(PAL["ui_bg"])

    # Animated background trees
    for i in range(25):
        bx = (i*173 + frame//3) % SW
        by = SH//2 + int(math.sin(i*0.8+frame*0.01)*30)
        col_v = 22 + i%18
        pygame.draw.circle(surf, (col_v, col_v+60, col_v), (bx, by), 6+i%8)

    # Title
    sh = Fm.render("FOREST  SURVIVAL", True, (0,40,0))
    ti = Fm.render("FOREST  SURVIVAL", True, PAL["ui_gold"])
    ox = SW//2 - ti.get_width()//2
    surf.blit(sh, (ox+3, 78)); surf.blit(ti, (ox, 75))
    sub = Fs.render("เกมเอาตัวรอดในป่า  •  v3.0  •  Python + Pygame", True, PAL["ui_dim"])
    surf.blit(sub, (SW//2-sub.get_width()//2, 142))

    # Input area
    area_x = SW//2-220
    _panel(surf, area_x, 175, 440, 160, 210)

    nl = F.render("ชื่อตัวละคร", True, PAL["ui_gold"])
    surf.blit(nl, (area_x+20, 192))
    ir = pygame.Rect(area_x+20, 220, 400, 42)
    pygame.draw.rect(surf, (20,32,18), ir, border_radius=6)
    bc = PAL["ui_gold"] if inp_on else PAL["ui_border"]
    pygame.draw.rect(surf, bc, ir, 2, border_radius=6)
    disp = inp + ("|" if inp_on and frame%60<30 else "")
    surf.blit(F.render(disp or "พิมพ์ชื่อที่นี่…", True, PAL["ui_text"] if inp else PAL["ui_dim"]),
              (ir.x+12, ir.y+9))

    # Buttons
    bnew  = pygame.Rect(SW//2-210, 360, 185, 52)
    bcust = pygame.Rect(SW//2+25,  360, 216, 52)
    bquit = pygame.Rect(SW//2-80,  428, 160, 42)
    _btn(surf, bnew,  "เริ่มเกม",             F, bnew.collidepoint(mouse),  not inp.strip())
    _btn(surf, bcust, "แต่งตัว / เลือกด่าน", F, bcust.collidepoint(mouse))
    _btn(surf, bquit, "ออก",                      F, bquit.collidepoint(mouse))

    tips = ["กดคลิกซ้ายหรือ SPACE เพื่อโจมตี  •  E เพื่อตัด/ขุด",
            "สร้างกองไฟก่อนกลางคืน — กลางคืนอันตรายกว่ามาก",
            "ดื่มน้ำ (G) ใกล้แหล่งน้ำ  •  กิน (F) เพื่อเพิ่มพลังงาน"]
    surf.blit(Fs.render(tips[frame//220%len(tips)], True, PAL["ui_dim"]),
              (SW//2-200, SH-38))

    return bnew, bcust, bquit, ir


def draw_customize(surf, fonts, mouse, cos, diff_idx, frame):
    F, Fm, Fs = fonts
    surf.fill((8,12,8))

    # Title bar
    pygame.draw.rect(surf, (18,30,16), (0,0,SW,65))
    pygame.draw.line(surf, PAL["ui_border"], (0,65),(SW,65), 1)
    t = F.render("แต่งตัวตัวละคร  &  เลือกด่านความยาก", True, PAL["ui_gold"])
    surf.blit(t, (SW//2-t.get_width()//2, 18))

    # Preview
    px, py = 170, SH//2
    _panel(surf, 40, 90, 220, SH-170, 190)
    _draw_preview(surf, px, py, cos)
    wname = WEAPON_DATA.get(cos["weapon"],WEAPON_DATA["fists"])["name"]
    pt = Fs.render(f"{cos['hat']}  •  {wname}", True, PAL["ui_dim"])
    surf.blit(pt, (px-pt.get_width()//2, py+70))

    # Options panel
    _panel(surf, 280, 90, SW-320, SH-170, 200)

    row_defs = [
        ("สีผิว",       "skin",   SKIN_COLS,  True),
        ("สีผม",        "hair",   HAIR_COLS,  True),
        ("สีเสื้อ",     "shirt",  SHIRT_COLS, True),
        ("สีกางเกง",    "pants",  PANTS_COLS, True),
        ("หมวก",        "hat",    HATS,       False),
        ("อาวุธเริ่มต้น","weapon", START_WEPS, False),
    ]
    labels = {"none":"ไม่มี","cap":"หมวก","helmet":"เกราะ","crown":"มงกุฎ","hood":"ฮู้ด",
              "fists":"กำปั้น","stone_knife":"มีดหิน","wooden_spear":"หอก","iron_sword":"ดาบ"}

    swatches = {}
    for ri, (lbl, key, opts, is_col) in enumerate(row_defs):
        ry = 102 + ri*70
        lt = Fs.render(lbl, True, PAL["ui_gold"])
        surf.blit(lt, (295, ry))
        row_sw = []
        for ci, opt in enumerate(opts):
            rx = 295 + ci*60; rr = pygame.Rect(rx, ry+22, 50, 36)
            sel = cos[key] == opt
            if is_col:
                _swatch(surf, rr, opt, sel)
            else:
                bg = (55,38,88) if sel else (28,38,26)
                pygame.draw.rect(surf, bg, rr, border_radius=5)
                pygame.draw.rect(surf, PAL["ui_gold"] if sel else (50,65,48), rr, 2 if sel else 1, border_radius=5)
                tl = Fs.render(labels.get(opt,opt), True, PAL["ui_text"])
                surf.blit(tl, (rr.x+rr.w//2-tl.get_width()//2, rr.y+rr.h//2-tl.get_height()//2))
            row_sw.append((rr, opt))
        swatches[key] = row_sw

    # Difficulty row
    dy = SH - 155
    dt = F.render("ด่านความยาก:", True, PAL["ui_gold"])
    surf.blit(dt, (295, dy-28))
    dbts = []
    for i, d in enumerate(DIFFS):
        dr = pygame.Rect(295+i*190, dy, 182, 52)
        sel = i==diff_idx
        bg = tuple(min(255,c+20) for c in d["col"]) if sel else tuple(c//4 for c in d["col"])
        pygame.draw.rect(surf, bg, dr, border_radius=7)
        pygame.draw.rect(surf, d["col"], dr, 3 if sel else 1, border_radius=7)
        nt = Fs.render(d["name"], True, PAL["white"])
        surf.blit(nt, (dr.x+dr.w//2-nt.get_width()//2, dr.y+dr.h//2-nt.get_height()//2))
        dbts.append(dr)
    ddesc = Fs.render(DIFFS[diff_idx]["desc"], True, DIFFS[diff_idx]["col"])
    surf.blit(ddesc, (295, dy+60))

    bok  = pygame.Rect(SW//2-80,  SH-75, 160, 46)
    bback= pygame.Rect(55, SH-75, 140, 46)
    _btn(surf, bok,  "ยืนยัน", F, bok.collidepoint(mouse))
    _btn(surf, bback,"กลับ",   F, bback.collidepoint(mouse))
    return swatches, dbts, bok, bback


def _draw_preview(surf, px, py, cos):
    skin = cos["skin"]; hair=cos["hair"]; shirt=cos["shirt"]; pants=cos["pants"]; hat=cos["hat"]
    pygame.draw.ellipse(surf, PAL["shadow"], (px-15, py+18, 30, 10))
    pygame.draw.line(surf, pants, (px-5, py+10),(px-5, py+26), 7)
    pygame.draw.line(surf, pants, (px+5, py+10),(px+5, py+26), 7)
    pygame.draw.rect(surf, shirt, (px-12, py-8, 24, 20), border_radius=4)
    pygame.draw.line(surf, skin, (px-12, py-2),(px-20, py+10), 5)
    pygame.draw.line(surf, skin, (px+12, py-2),(px+20, py+10), 5)
    pygame.draw.circle(surf, skin, (px, py-16), 14)
    pygame.draw.arc(surf, hair, pygame.Rect(px-14, py-30, 28, 20), 0, math.pi, 5)
    hx, hy = px, py-30
    if hat=="cap":
        pygame.draw.ellipse(surf, (30,90,30),(hx-16,hy+2,32,10))
        pygame.draw.rect(surf, (30,90,30),(hx-11,hy-8,22,12), border_radius=3)
    elif hat=="helmet":
        pygame.draw.arc(surf,(155,155,170),pygame.Rect(hx-15,hy-5,30,20),0,math.pi,11)
    elif hat=="crown":
        pts=[(hx-11,hy+2),(hx-9,hy-9),(hx-4,hy),(hx,hy-11),(hx+4,hy),(hx+9,hy-9),(hx+11,hy+2)]
        pygame.draw.polygon(surf, PAL["ui_gold"], pts)
    elif hat=="hood":
        pygame.draw.arc(surf,(38,38,78),pygame.Rect(hx-17,hy-6,34,22),0,math.pi,18)


def draw_hud(surf, p, fonts, ps):
    F, Fm, Fs = fonts
    # Left stat panel — slim and clean
    pw, ph = 248, 195
    _panel(surf, 10, 10, pw, ph, 195)

    bw, bh = pw-24, 17; bx = 22
    hp_col = PAL["hp"] if p.hp/p.mhp > 0.35 else PAL["hp_low"]
    _bar(surf, bx, 18,  bw, bh, p.hp,      p.mhp,   hp_col,        "❤",  Fs)
    _bar(surf, bx, 42,  bw, bh, p.hunger,  100,     PAL["hunger"], "🍗", Fs)
    _bar(surf, bx, 66,  bw, bh, p.thirst,  100,     PAL["thirst"], "💧", Fs)
    _bar(surf, bx, 90,  bw, bh, p.stamina, 100,     PAL["stamina"],"⚡", Fs)
    _bar(surf, bx, 114, bw, bh, p.xp,      p.xp_next,PAL["xp"],   "✨", Fs)

    t = Fs.render(f"Lv.{p.level}   📅 วันที่ {p.day}   🗡 {p.kills} kills", True, PAL["ui_gold"])
    surf.blit(t, (18, 138))
    wn = WEAPON_DATA.get(p.weapon,WEAPON_DATA["fists"])["name"]
    t2 = Fs.render(f"{wn}   DEF +{p.armor}   [{p.diff['name']}]", True, PAL["ui_dim"])
    surf.blit(t2, (18, 160))

    # Poison indicator
    if p.poison_stacks > 0:
        pt = Fs.render(f"พิษ ×{p.poison_stacks}", True, (80,230,100))
        surf.blit(pt, (18, 180))

    # ── Top-right: Day + Time panel ──
    t3 = p.gtime % 10
    if   t3 < 2:  tod = "🌅 รุ่งเช้า";   todcol = (255, 210,  80); phase = 0
    elif t3 < 5:  tod = "☀  กลางวัน";   todcol = (230, 220,  60); phase = 1
    elif t3 < 7:  tod = "🌆 พลบค่ำ";   todcol = (230, 130,  40); phase = 2
    else:          tod = "🌙 กลางคืน";  todcol = (140, 140, 220); phase = 3

    # Check fire nearby
    near_fire = any(math.hypot(p.x-fx,p.y-fy)<TILE*5 for fx,fy in p.campfires)
    near_torch = any(math.hypot(p.x-tx,p.y-ty)<TILE*3 for tx,ty in p.torches)
    has_light = near_fire or near_torch

    # Panel background
    pan_w, pan_h = 220, 80
    pan_x, pan_y = SW - pan_w - 8, 8
    _panel(surf, pan_x, pan_y, pan_w, pan_h, 210)

    # Day number (big)
    day_txt = F.render(f"📅 วันที่  {p.day}", True, PAL["ui_gold"])
    surf.blit(day_txt, (pan_x + pan_w//2 - day_txt.get_width()//2, pan_y + 6))

    # Time of day label
    tod_txt = Fs.render(tod, True, todcol)
    surf.blit(tod_txt, (pan_x + pan_w//2 - tod_txt.get_width()//2, pan_y + 28))

    # Progress bar + percentage for the day
    prog = t3 / 10.0
    pct  = int(prog * 100)
    bar_w = pan_w - 16; bar_x = pan_x + 8; bar_y = pan_y + 48

    # Bar background
    pygame.draw.rect(surf, (20, 30, 18), (bar_x, bar_y, bar_w, 10), border_radius=5)

    # Bar fill — pulses red when >85%
    if prog > 0.85:
        pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.006)) * 80)
        bar_col = (200 + pulse//2, 60, 30)
    elif phase < 2:
        bar_col = (200, 180, 40)
    elif phase == 2:
        bar_col = (200, 100, 30)
    else:
        bar_col = (80, 80, 180)
    pygame.draw.rect(surf, bar_col, (bar_x, bar_y, int(bar_w*prog), 10), border_radius=5)
    pygame.draw.rect(surf, PAL["ui_border"], (bar_x, bar_y, bar_w, 10), 1, border_radius=5)

    # Percentage label
    if prog > 0.85:
        pct_col = (255, 100, 60)
        pct_txt = Fs.render(f"{pct}%  ⚠ ใกล้จบวัน!", True, pct_col)
    else:
        pct_col = PAL["ui_dim"]
        pct_txt = Fs.render(f"{pct}%", True, pct_col)
    surf.blit(pct_txt, (pan_x + pan_w//2 - pct_txt.get_width()//2, pan_y + 60))

    # Fire warning — shown when dusk/night and no fire nearby
    if phase >= 2 and not has_light:
        warn_pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.004)) * 200) + 55
        warn_col   = (warn_pulse, 60, 20)
        fire_txt   = F.render("🔥 จุดไฟด่วน!" if phase == 3 else "🔥 เตรียมจุดไฟ!", True, warn_col)
        fw_x = pan_x + pan_w//2 - fire_txt.get_width()//2
        fw_y = pan_y + pan_h + 4
        # Warn background
        warn_bg = pygame.Surface((fire_txt.get_width()+16, fire_txt.get_height()+8), pygame.SRCALPHA)
        warn_bg.fill((60, 15, 5, 200))
        surf.blit(warn_bg, (fw_x - 8, fw_y - 4))
        surf.blit(fire_txt, (fw_x, fw_y))
    elif phase >= 2 and has_light:
        # Safe indicator
        safe_txt = Fs.render("🔥 ปลอดภัย", True, (80, 200, 80))
        surf.blit(safe_txt, (pan_x + pan_w//2 - safe_txt.get_width()//2, pan_y + pan_h + 4))

    # Attack cooldown bar (bottom center, only when cooling)
    if p.atk_cd > 0:
        cd_ratio = p.atk_cd / p.atk_cd_max()
        bw2 = 120; bx2 = SW//2-bw2//2; by2 = SH-50
        pygame.draw.rect(surf, (30,30,30), (bx2-1, by2-1, bw2+2, 14), border_radius=7)
        pygame.draw.rect(surf, PAL["red"],  (bx2, by2, int(bw2*(1-cd_ratio)), 12), border_radius=7)
        pygame.draw.rect(surf, PAL["ui_border"], (bx2-1, by2-1, bw2+2, 14), 1, border_radius=7)

    # Key hints — minimal, at very bottom
    hints = Fs.render("WASD=เดิน  SHIFT=วิ่ง  คลิก/SPACE=โจมตี  E=ตัด  F=กิน  G=ดื่ม  C=คราฟต์  I=กระเป๋า  B=วางของ  V=ฟาร์ม  M=ด่าน  P/ESC=หยุด",
                      True, PAL["ui_dim"])
    surf.blit(hints, (SW//2-hints.get_width()//2, SH-18))


def draw_inventory(surf, fonts, p, scroll, mouse):
    F, Fm, Fs = fonts
    ow, oh = 680, 500; ox = SW//2-ow//2; oy = SH//2-oh//2
    _panel(surf, ox, oy, ow, oh, 230)
    pygame.draw.rect(surf, PAL["ui_border"], (ox,oy,ow,oh), 1, border_radius=8)

    t = F.render("กระเป้าเป้", True, PAL["ui_gold"])
    surf.blit(t, (ox+ow//2-t.get_width()//2, oy+14))

    items = list(p.inv.items())
    cols=5; cs=108; rs=86; sx_=ox+(ow-cols*cs)//2; sy_=oy+52
    hover_item = None

    for idx,(iid,qty) in enumerate(items):
        c, r = idx%cols, idx//cols-scroll
        if r<0 or r>=4: continue
        rx=sx_+c*cs; ry=sy_+r*rs
        cr=pygame.Rect(rx,ry,cs-6,rs-6)
        hov = cr.collidepoint(mouse)
        if hov: hover_item=(iid,qty)
        bg = (45,72,40) if hov else (22,38,18)
        pygame.draw.rect(surf, bg, cr, border_radius=6)
        pygame.draw.rect(surf, PAL["ui_border"], cr, 1, border_radius=6)
        # Equip glow
        if p.weapon==iid or (iid in("armor","iron_armor") and p.armor>0):
            pygame.draw.rect(surf, PAL["ui_gold"], cr, 2, border_radius=6)

        # Icon circle
        ic = ITEM_COLS.get(iid, (150,150,150))
        pygame.draw.circle(surf, ic, (rx+24, ry+24), 17)
        pygame.draw.circle(surf, tuple(min(255,c+40) for c in ic), (rx+18, ry+18), 7)
        pygame.draw.circle(surf, (20,30,18), (rx+24, ry+24), 17, 1)

        n_t = Fs.render(ITEM_NAMES.get(iid,iid), True, PAL["ui_text"])
        q_t = Fs.render(f"×{qty}", True, PAL["ui_gold"])
        surf.blit(n_t, (rx+46, ry+8))
        surf.blit(q_t, (rx+46, ry+26))
        hint_t = Fs.render("คลิก=ใช้", True, PAL["ui_dim"])
        surf.blit(hint_t, (rx+6, ry+rs-22))

    if hover_item:
        ic = ITEM_COLS.get(hover_item[0],(150,150,150))
        tip = F.render(f"{ITEM_NAMES.get(hover_item[0],hover_item[0])}  ×{hover_item[1]}", True, ic)
        surf.blit(tip, (min(mouse[0]+12, SW-tip.get_width()-10), max(mouse[1]-35, 5)))

    cb = pygame.Rect(ox+ow//2-55, oy+oh-44, 110, 34)
    _btn(surf, cb, "ปิด [I]", F, cb.collidepoint(mouse))
    return items, cb


def draw_craft(surf, fonts, p, scroll, mouse):
    F, Fm, Fs = fonts
    ow, oh = 720, 530; ox = SW//2-ow//2; oy = SH//2-oh//2
    _panel(surf, ox, oy, ow, oh, 230)
    pygame.draw.rect(surf, PAL["ui_border"], (ox,oy,ow,oh), 1, border_radius=8)

    t = F.render("โต๊ะคราฟต์", True, PAL["ui_gold"])
    surf.blit(t, (ox+ow//2-t.get_width()//2, oy+14))

    craft_idx = None
    per_page = 5
    for i, rec in enumerate(RECIPES[scroll:scroll+per_page]):
        ri = i+scroll; ry = oy+52+i*87
        can = p.has(rec["needs"])
        rr = pygame.Rect(ox+12, ry, ow-24, 82)
        hov = rr.collidepoint(mouse)
        bg = (50,85,45) if (hov and can) else ((28,50,25) if can else (38,28,28))
        pygame.draw.rect(surf, bg, rr, border_radius=7)
        bc = PAL["ui_border"] if can else (80,35,35)
        pygame.draw.rect(surf, bc, rr, 1, border_radius=7)

        ic = ITEM_COLS.get(rec["id"],(150,150,150))
        pygame.draw.circle(surf, ic, (ox+46, ry+41), 22)
        pygame.draw.circle(surf, tuple(min(255,c+40) for c in ic), (ox+40, ry+35), 9)
        pygame.draw.circle(surf, (20,30,18), (ox+46, ry+41), 22, 1)

        nt = F.render(rec["name"], True, PAL["ui_gold"] if can else PAL["ui_dim"])
        surf.blit(nt, (ox+80, ry+8))
        dt = Fs.render(rec["desc"], True, PAL["ui_dim"])
        surf.blit(dt, (ox+80, ry+30))
        mats = "ต้องการ: " + "  ".join(
            f"{ITEM_NAMES.get(k,k)} ×{v}  [{p.inv.get(k,0)}]" for k,v in rec["needs"].items())
        mc = (80,180,80) if can else (180,60,60)
        mt = Fs.render(mats, True, mc)
        surf.blit(mt, (ox+80, ry+52))
        if hov and can: craft_idx = ri

    # Scroll indicators
    if scroll > 0:
        surf.blit(Fs.render("▲", True, PAL["ui_dim"]), (ox+ow-28, oy+56))
    if scroll+per_page < len(RECIPES):
        surf.blit(Fs.render("▼", True, PAL["ui_dim"]), (ox+ow-28, oy+oh-65))

    cb = pygame.Rect(ox+ow//2-55, oy+oh-44, 110, 34)
    _btn(surf, cb, "ปิด [C]", F, cb.collidepoint(mouse))
    return craft_idx, cb


def draw_pause(surf, fonts, mouse):
    F, Fm, Fs = fonts
    ov = pygame.Surface((SW,SH), pygame.SRCALPHA); ov.fill((0,0,0,145)); surf.blit(ov,(0,0))
    t = Fm.render("หยุดชั่วคราว", True, PAL["ui_gold"])
    surf.blit(t, (SW//2-t.get_width()//2, 190))
    bs = {}
    for i,(lbl,k) in enumerate([("กลับเล่น","resume"),
                                  ("เลือกด่าน","stages"),("ตั้งค่า","settings"),("เมนูหลัก","menu")]):
        r = pygame.Rect(SW//2-140, 260+i*60, 280, 48)
        _btn(surf, r, lbl, F, r.collidepoint(mouse))
        bs[k] = r
    return bs


def draw_settings(surf, fonts, audio, mouse):
    F, Fm, Fs = fonts
    ow, oh = 560, 480; ox = SW//2-ow//2; oy = SH//2-oh//2
    _panel(surf, ox, oy, ow, oh, 228)
    pygame.draw.rect(surf, PAL["ui_border"], (ox,oy,ow,oh), 1, border_radius=8)
    t = F.render("ตั้งค่า", True, PAL["ui_gold"])
    surf.blit(t, (ox+ow//2-t.get_width()//2, oy+14))

    # ── BGM toggle + slider ──
    bgm_btn = pygame.Rect(ox+30, oy+58, 200, 38)
    bgm_lbl = "🎵 ดนตรี: เปิด" if audio.bgm_on else "🎵 ดนตรี: ปิด"
    _btn(surf, bgm_btn, bgm_lbl, Fs, bgm_btn.collidepoint(mouse))

    surf.blit(Fs.render(f"ระดับดนตรี  {int(audio.bgm_vol*100)}%", True, PAL["ui_text"]), (ox+30, oy+104))
    bgm_slr = pygame.Rect(ox+30, oy+122, ow-60, 14)
    pygame.draw.rect(surf, (25,35,22), bgm_slr, border_radius=7)
    pw1 = int((ow-60)*audio.bgm_vol)
    if pw1 > 0:
        pygame.draw.rect(surf, (70,170,230), (ox+30, oy+122, pw1, 14), border_radius=7)
        pygame.draw.rect(surf, (100,200,255), (ox+30, oy+122, pw1, 6), border_radius=7)
    pygame.draw.rect(surf, PAL["ui_border"], bgm_slr, 1, border_radius=7)
    # Thumb
    tx1 = ox+30+pw1; pygame.draw.circle(surf, PAL["ui_gold"], (tx1, oy+122+7), 9)

    # ── SFX toggle + slider ──
    sfx_btn = pygame.Rect(ox+30, oy+155, 200, 38)
    sfx_lbl = "🔊 เอฟเฟกต์: เปิด" if audio.sfx_on else "🔇 เอฟเฟกต์: ปิด"
    _btn(surf, sfx_btn, sfx_lbl, Fs, sfx_btn.collidepoint(mouse))

    surf.blit(Fs.render(f"ระดับเอฟเฟกต์  {int(audio.sfx_vol*100)}%", True, PAL["ui_text"]), (ox+30, oy+201))
    sfx_slr = pygame.Rect(ox+30, oy+219, ow-60, 14)
    pygame.draw.rect(surf, (25,35,22), sfx_slr, border_radius=7)
    pw2 = int((ow-60)*audio.sfx_vol)
    if pw2 > 0:
        pygame.draw.rect(surf, PAL["hunger"], (ox+30, oy+219, pw2, 14), border_radius=7)
        pygame.draw.rect(surf, (255,200,100), (ox+30, oy+219, pw2, 6), border_radius=7)
    pygame.draw.rect(surf, PAL["ui_border"], sfx_slr, 1, border_radius=7)
    tx2 = ox+30+pw2; pygame.draw.circle(surf, PAL["ui_gold"], (tx2, oy+219+7), 9)

    # ── Controls reference ──
    pygame.draw.line(surf, PAL["ui_border"], (ox+20, oy+248), (ox+ow-20, oy+248), 1)
    surf.blit(Fs.render("การควบคุม", True, PAL["ui_gold"]), (ox+30, oy+256))
    ctrl = [("WASD / ←↑↓→","เดิน"),("SHIFT","วิ่ง"),("คลิกซ้าย / SPACE","โจมตี"),
            ("E","ตัด / ขุด"),("F","กินอาหาร"),("G","ดื่มน้ำ"),
            ("C","คราฟต์"),("I","กระเป้า"),("P","วางของ"),("M","เลือกด่าน")]
    for j,(k,v) in enumerate(ctrl):
        col_x = ox+30+(j//5)*260; row_y = oy+276+(j%5)*28
        surf.blit(Fs.render(k, True, PAL["ui_gold"]), (col_x, row_y))
        surf.blit(Fs.render(f"= {v}", True, PAL["ui_dim"]), (col_x+120, row_y))

    cb = pygame.Rect(ox+ow//2-55, oy+oh-46, 110, 34)
    _btn(surf, cb, "ปิด [ESC]", F, cb.collidepoint(mouse))
    # Return all interactive rects
    return bgm_btn, bgm_slr, sfx_btn, sfx_slr, cb


def draw_gameover(surf, fonts, p, mouse, frame):
    F, Fm, Fs = fonts
    surf.fill((10,4,4))
    # Subtle vignette
    for r in range(400,0,-30):
        alpha = max(0, 60 - r//8)
        s = pygame.Surface((SW,SH), pygame.SRCALPHA)
        pygame.draw.rect(s, (0,0,0,alpha), (SW//2-r, SH//2-r, r*2, r*2), border_radius=r)
        surf.blit(s,(0,0))

    rv = int(155+80*math.sin(frame*0.055))
    ti = Fm.render("เกมจบแล้ว", True, (rv,18,18))
    surf.blit(ti, (SW//2-ti.get_width()//2, 105))

    if p:
        # Stats box
        _panel(surf, SW//2-200, 185, 400, 230, 210)
        stats = [
            ("ชื่อ",         getattr(p,"name","?")),
            ("เลเวล",        str(getattr(p,"level",1))),
            ("อยู่รอด",      f"{getattr(p,'survived',0)} วัน"),
            ("ฆ่าศัตรู",     f"{getattr(p,'kills',0)} ตัว"),
            ("คราฟต์",       f"{getattr(p,'crafted',0)} ครั้ง"),
            ("ด่าน",         getattr(p,"diff",{"name":"?"}).get("name","?")),
        ]
        for i,(k,v) in enumerate(stats):
            ky = F.render(k, True, PAL["ui_dim"])
            vt = F.render(v, True, PAL["ui_text"])
            rx = SW//2-190; ry = 200+i*34
            surf.blit(ky, (rx, ry))
            surf.blit(vt, (rx+180, ry))

    bret  = pygame.Rect(SW//2-260, 435, 220, 52)
    bmenu = pygame.Rect(SW//2+40,  435, 220, 52)
    bcust = pygame.Rect(SW//2-85,  500, 170, 42)
    _btn(surf, bret,  "ลองใหม่", F, bret.collidepoint(mouse))
    _btn(surf, bmenu, "เมนูหลัก", F, bmenu.collidepoint(mouse))
    _btn(surf, bcust, "เปลี่ยนตัวละคร", Fs, bcust.collidepoint(mouse))
    return bret, bmenu, bcust


def day_night(surf, p, night_surf=None):
    t = p.gtime % 10
    if t < 5:    alpha = 0
    elif t < 6:  alpha = int((t-5)*110)
    elif t < 9:  alpha = min(190, 110+int((t-6)*30))
    else:        alpha = int((10-t)*65)
    nf = any(math.hypot(p.x-fx,p.y-fy)<TILE*5 for fx,fy in p.campfires)
    nt = any(math.hypot(p.x-tx,p.y-ty)<TILE*3 for tx,ty in p.torches)
    if nf or nt: alpha = max(0, alpha-90)
    if alpha > 0:
        if night_surf is None:
            night_surf = pygame.Surface((SW,SH), pygame.SRCALPHA)
        night_surf.fill((8,4,28,alpha))
        surf.blit(night_surf,(0,0))

# ─────────────────────────────────────────────────────
