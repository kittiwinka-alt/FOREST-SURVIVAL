"""
renderer.py — วาด objects ในโลก (trees, ores, campfire, shelter, house, farm)
"""
import math
import random
import pygame
from config import PAL, TILE

def draw_tree(surf, x, y, stage=3):
    """Draw a layered tree — more realistic multi-blob canopy"""
    # Roots/shadow
    pygame.draw.ellipse(surf, PAL["shadow"], (x-18, y+14, 36, 10))
    # Trunk
    tw = 6 + stage
    pygame.draw.rect(surf, PAL["tree_trunk"], (x-tw//2, y-8, tw, 22))
    pygame.draw.rect(surf, (70,42,15), (x-tw//2, y-8, 2, 22))
    # Canopy — layered circles for depth
    r = 14 + stage*4
    layers = [PAL["tree_dark"], PAL["tree_mid"], PAL["tree_light"]]
    offsets = [(0,-r+2), (0,-r-4), (0,-r-10)]
    for col, (ox,oy) in zip(layers, offsets):
        pygame.draw.circle(surf, col, (x+ox, y+oy), r-2)
    # highlight blob
    pygame.draw.circle(surf, PAL["tree_light"], (x+6, y-r-4), r//3)

def draw_bush(surf, x, y):
    pygame.draw.ellipse(surf, PAL["shadow"], (x-14, y+8, 28, 8))
    pygame.draw.circle(surf, (35,110,35), (x, y), 14)
    pygame.draw.circle(surf, (50,140,50), (x-7, y-4), 10)
    pygame.draw.circle(surf, (50,140,50), (x+7, y-4), 10)
    pygame.draw.circle(surf, (60,155,55), (x, y-10), 9)
    for bx,by in [(-6,-2),(5,-3),(0,4),(-2,-7),(7,2)]:
        pygame.draw.circle(surf, (195,55,75), (x+bx, y+by), 3)

def draw_ore(surf, x, y, stage=2):
    """Rocky ore outcrop"""
    pygame.draw.ellipse(surf, PAL["shadow"], (x-18, y+12, 36, 8))
    cols = [(95,95,102),(110,110,118),(130,130,138)]
    for i, (ox,oy,r) in enumerate([(0,0,16),(-10,-6,12),(10,-5,11),(0,-14,10)]):
        pygame.draw.ellipse(surf, cols[min(i,2)], (x+ox-r, y+oy-r//2, r*2, r))
    # Iron veins if ore
    if stage > 1:
        for _ in range(3):
            ex = x + random.randint(-10,10)
            ey = y + random.randint(-8,4)
            pygame.draw.circle(surf, (160,120,60), (ex,ey), random.randint(2,4))

def draw_mushroom(surf, x, y):
    pygame.draw.rect(surf, (220,200,175), (x-3, y, 6, 10))
    pygame.draw.ellipse(surf, (180,55,50), (x-12, y-10, 24, 16))
    for dx in [-5,0,5]: pygame.draw.circle(surf, (240,225,210), (x+dx, y-5), 2)

def draw_reed(surf, x, y):
    for dx in [-5,0,5]:
        pygame.draw.line(surf, (110,160,65), (x+dx, y+10), (x+dx+dx//2, y-16), 2)
        pygame.draw.ellipse(surf, (145,100,45), (x+dx-3, y-22, 6, 12))

def draw_flower(surf, x, y):
    for i in range(6):
        a = i*math.pi/3
        px, py = x+int(math.cos(a)*5), y+int(math.sin(a)*5)
        col = random.choice([(220,80,80),(220,180,50),(80,120,220),(180,80,200)])
        pygame.draw.circle(surf, col, (px,py), 3)
    pygame.draw.circle(surf, (240,220,60), (x,y), 4)

def draw_campfire(surf, x, y, ps):
    pygame.draw.circle(surf, (60,55,50), (x, y+10), 12)
    for i, (ox,s) in enumerate([(-8,0),(8,0),(0,-4)]):
        pygame.draw.line(surf, PAL["tree_trunk"], (x+ox, y+10), (x, y-2), 3)
    ps.fire(x, y-2)
    _glow = pygame.Surface((80,80))
    _glow.set_colorkey((0,0,0))
    _glow.set_alpha(30)
    _glow.fill((0,0,0))
    pygame.draw.circle(_glow, (255,140,40), (40,40), 38)
    surf.blit(_glow, (x-40, y-40), special_flags=pygame.BLEND_ADD)

def draw_shelter(surf, x, y):
    pygame.draw.polygon(surf, (90,58,22), [(x-28,y+18),(x+28,y+18),(x,y-20)])
    pygame.draw.polygon(surf, (75,48,15), [(x-28,y+18),(x-26,y+16),(x,y-18),(x+26,y+16),(x+28,y+18)])
    pygame.draw.rect(surf, (55,35,10), (x-9,y+5,18,13))

def draw_torch(surf, x, y, ps):
    pygame.draw.line(surf, PAL["tree_trunk"], (x, y+12), (x-2, y-8), 3)
    pygame.draw.circle(surf, (200,110,30), (x-2, y-10), 5)
    ps.fire(x-2, y-10)

def draw_house(surf, x, y):
    """Draw a cozy log house."""
    # Shadow
    pygame.draw.ellipse(surf, PAL["shadow"], (x-38, y+32, 76, 14))
    # Walls
    pygame.draw.rect(surf, (140,100,55), (x-32, y-10, 64, 44), border_radius=3)
    pygame.draw.rect(surf, (115,80,38), (x-32, y-10, 6, 44))     # left shadow
    # Door
    pygame.draw.rect(surf, (80,52,22), (x-8, y+12, 16, 22), border_radius=2)
    pygame.draw.circle(surf, (220,180,80), (x+6, y+23), 2)         # doorknob
    # Windows
    for wx in [-20, 12]:
        pygame.draw.rect(surf, (140,200,230), (x+wx, y-2, 10, 10), border_radius=1)
        pygame.draw.rect(surf, (80,60,30),    (x+wx, y-2, 10, 10), 1, border_radius=1)
        pygame.draw.line(surf, (80,60,30), (x+wx+5, y-2), (x+wx+5, y+8), 1)
        pygame.draw.line(surf, (80,60,30), (x+wx, y+3),   (x+wx+10,y+3), 1)
    # Roof
    pts = [(x-38, y-10),(x+38, y-10),(x+22, y-38),(x-22, y-38)]
    pygame.draw.polygon(surf, (100,60,25), pts)
    pygame.draw.polygon(surf, (80,45,15), pts, 2)
    # Roof ridge
    pygame.draw.line(surf, (65,38,12), (x-22, y-38), (x+22, y-38), 3)
    # Chimney
    pygame.draw.rect(surf, (120,90,55), (x+16, y-46, 10, 20))
    pygame.draw.rect(surf, (100,70,40), (x+14, y-50, 14,  6), border_radius=2)

def draw_farm_plot(surf, x, y, plot, frame):
    """Draw a farm plot with crop growth stages."""
    CROP_COLS = {"carrot":(230,120,30),"potato":(195,165,100),"cabbage":(70,180,70)}
    # Soil base
    pygame.draw.rect(surf, (90,58,28), (x-22, y-12, 44, 28), border_radius=3)
    pygame.draw.rect(surf, (70,45,18), (x-22, y-12, 44, 28), 1, border_radius=3)
    # Tilled rows
    for ry in range(3):
        pygame.draw.line(surf, (110,72,35), (x-18, y-6+ry*7), (x+18, y-6+ry*7), 1)
    # Water indicator
    if plot["water"] > 20:
        ww = int(44 * min(1.0, plot["water"]/100))
        pygame.draw.rect(surf, (60,100,200), (x-22, y+12, ww, 4), border_radius=2)

    if not plot["crop"]: return
    stage = plot["stage"]
    col   = CROP_COLS.get(plot["crop"], (80,180,80))
    if stage < 0.33:
        # Sprout
        pygame.draw.line(surf, (80,160,60), (x, y+4), (x, y-4), 2)
        pygame.draw.circle(surf, (100,190,70), (x, y-5), 3)
    elif stage < 0.66:
        # Growing
        pygame.draw.line(surf, (70,145,50), (x, y+6), (x, y-8), 3)
        pygame.draw.ellipse(surf, col, (x-7, y-16, 14, 10))
    elif stage < 1.0:
        # Almost ready
        pygame.draw.line(surf, (60,130,45), (x-3, y+6), (x-3, y-10), 3)
        pygame.draw.ellipse(surf, col, (x-10, y-18, 18, 14))
        sway = int(math.sin(frame*0.05)*2)
        pygame.draw.circle(surf, (min(255,col[0]+40), col[1], col[2]), (x+3+sway, y-14), 5)
    else:
        # Ready to harvest! Pulse glow
        glow_a = int(120 + 80*math.sin(frame*0.12))
        _fg = pygame.Surface((50,50))
        _fg.set_colorkey((0,0,0)); _fg.fill((0,0,0))
        _fg.set_alpha(glow_a)
        pygame.draw.circle(_fg, col, (25,25), 22)
        surf.blit(_fg, (x-25, y-28), special_flags=pygame.BLEND_ADD)
        # Full plant
        pygame.draw.line(surf, (55,120,40), (x-3, y+6), (x-3, y-12), 4)
        pygame.draw.ellipse(surf, col, (x-12, y-22, 22, 16))
        pygame.draw.circle(surf, tuple(min(255,c+50) for c in col), (x+5, y-16), 6)
        # "เก็บ!" label
        fnt = pygame.font.SysFont(None, 14)
        lbl = fnt.render("เก็บ! V", True, (240,230,50))
        surf.blit(lbl, (x - lbl.get_width()//2, y-36))


