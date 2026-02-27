"""
world.py — World generation และ tile rendering
"""
import random
import pygame
from config import PAL, TILE, TGRASS, TWATER, TDEEP, TMUD, TROCK, TSAND

# ─────────────────────────────────────────────────────
#  NOISE HELPERS
# ─────────────────────────────────────────────────────
def _hash(x, y, seed):
    n = int(x) * 1619 + int(y) * 31337 + int(seed) * 1013
    n = (n >> 13) ^ n
    return 1.0 - ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / 1073741824.0

def _smooth(x, y, seed, sc):
    fx, fy = x / sc, y / sc
    ix, iy = int(fx), int(fy)
    tx = (fx - ix); tx = tx * tx * (3 - 2 * tx)
    ty = (fy - iy); ty = ty * ty * (3 - 2 * ty)
    v = _hash(ix, iy, seed) * (1 - tx) + _hash(ix + 1, iy, seed) * tx
    w = _hash(ix, iy + 1, seed) * (1 - tx) + _hash(ix + 1, iy + 1, seed) * tx
    return v * (1 - ty) + w * ty


# ─────────────────────────────────────────────────────
#  TILE CACHE
# ─────────────────────────────────────────────────────
_tile_cache = {}

def _make_tile(tid, variant=0):
    rng = random.Random(tid * 997 + variant * 13)
    surf = pygame.Surface((TILE, TILE))
    if tid == TGRASS:
        surf.fill(PAL["grass1"])
        for _ in range(12):
            x, y = rng.randint(0, TILE-1), rng.randint(0, TILE-1)
            col = PAL["grass2"] if rng.random() > 0.5 else PAL["grass3"]
            pygame.draw.circle(surf, col, (x, y), rng.randint(2, 5))
    elif tid == TWATER:
        surf.fill(PAL["water1"])
        for _ in range(6):
            x, y = rng.randint(2, TILE-3), rng.randint(2, TILE-3)
            pygame.draw.ellipse(surf, PAL["water2"], (x, y, rng.randint(6, 12), rng.randint(2, 4)))
    elif tid == TDEEP:
        surf.fill((25, 65, 140))
        for _ in range(4):
            x, y = rng.randint(2, TILE-3), rng.randint(2, TILE-3)
            pygame.draw.ellipse(surf, (35, 80, 165), (x, y, rng.randint(4, 10), rng.randint(2, 4)))
    elif tid == TMUD:
        surf.fill(PAL["mud"])
        for _ in range(8):
            x, y = rng.randint(0, TILE-1), rng.randint(0, TILE-1)
            pygame.draw.circle(surf, (80, 55, 28), (x, y), rng.randint(2, 5))
    elif tid == TROCK:
        surf.fill(PAL["rock"])
        for _ in range(10):
            x, y = rng.randint(0, TILE-1), rng.randint(0, TILE-1)
            cv = rng.randint(90, 120)
            pygame.draw.circle(surf, (cv, cv, cv+5), (x, y), rng.randint(2, 5))
    elif tid == TSAND:
        surf.fill(PAL["sand"])
        for _ in range(8):
            x, y = rng.randint(0, TILE-1), rng.randint(0, TILE-1)
            pygame.draw.circle(surf, (180, 162, 95), (x, y), rng.randint(2, 4))
    return surf

def _precompute_tiles():
    """เรียกครั้งเดียวหลัง pygame.init() เพื่อ fill cache"""
    for tid in [TGRASS, TWATER, TDEEP, TMUD, TROCK, TSAND]:
        for v in range(16):
            _tile_cache[(tid, v)] = _make_tile(tid, v)

def get_tile_surf(tid, tx, ty):
    key = (tid, (tx * 7 + ty * 3) % 16)
    if key not in _tile_cache:
        _tile_cache[key] = _make_tile(tid, key[1])
    return _tile_cache[key]


# ─────────────────────────────────────────────────────
#  WORLD CLASS
# ─────────────────────────────────────────────────────
class World:
    W, H = 96, 72

    def __init__(self, seed=None):
        self.seed = seed or random.randint(1, 99999)
        random.seed(self.seed)
        self.tiles = [[TGRASS] * self.W for _ in range(self.H)]
        self.objs  = {}   # (tx,ty) → {"type","hp","stage"}
        self.drops = {}   # (tx,ty) → [{"id","qty"}]
        self._generate()

    def _generate(self):
        s = self.seed
        for ty in range(self.H):
            for tx in range(self.W):
                h = _smooth(tx, ty, s, 14)*0.5 + _smooth(tx, ty, s+1, 6)*0.3 + _smooth(tx, ty, s+2, 3)*0.2
                w = _smooth(tx, ty, s+7, 12)
                if w > 0.62:
                    self.tiles[ty][tx] = TDEEP if w > 0.75 else TWATER
                elif h < -0.35:
                    self.tiles[ty][tx] = TMUD
                elif h > 0.52:
                    self.tiles[ty][tx] = TROCK
                elif abs(_smooth(tx, ty, s+4, 7)) > 0.58:
                    self.tiles[ty][tx] = TSAND

        for ty in range(1, self.H-1):
            for tx in range(1, self.W-1):
                t = self.tiles[ty][tx]
                r = random.random()
                if t == TGRASS:
                    if   r < 0.065: self.objs[(tx, ty)] = {"type":"tree",     "hp":5, "stage":random.randint(2, 4)}
                    elif r < 0.095: self.objs[(tx, ty)] = {"type":"bush",     "hp":2, "stage":1}
                    elif r < 0.110: self.objs[(tx, ty)] = {"type":"mushroom", "hp":1, "stage":1}
                    elif r < 0.115: self.objs[(tx, ty)] = {"type":"flower",   "hp":1, "stage":1}
                elif t == TROCK and r < 0.22:
                    self.objs[(tx, ty)] = {"type":"ore", "hp":6, "stage":random.randint(1, 3)}
                elif t == TMUD and r < 0.06:
                    self.objs[(tx, ty)] = {"type":"reed", "hp":1, "stage":1}
                elif t == TSAND and r < 0.03:
                    self.objs[(tx, ty)] = {"type":"cactus", "hp":2, "stage":1}

    def walkable(self, tx, ty):
        if not (0 <= tx < self.W and 0 <= ty < self.H): return False
        if self.tiles[ty][tx] in (TWATER, TDEEP): return False
        obj = self.objs.get((tx, ty))
        if obj and obj["type"] in ("tree", "ore"): return False
        return True

    def hit(self, tx, ty, power=1):
        obj = self.objs.get((tx, ty))
        if not obj: return []
        obj["hp"] -= power
        drops = []
        if obj["hp"] <= 0:
            t = obj["type"]
            if t == "tree":
                drops = [{"id":"wood", "qty":random.randint(3, 6)}, {"id":"leaf", "qty":random.randint(2, 4)}]
                if random.random() < 0.35: drops.append({"id":"fruit", "qty":1})
                if random.random() < 0.15: drops.append({"id":"seed",  "qty":1})
            elif t == "ore":
                drops = [{"id":"stone", "qty":random.randint(3, 6)}]
                if random.random() < 0.3: drops.append({"id":"iron", "qty":random.randint(1, 2)})
            elif t == "bush":
                drops = [{"id":"berry", "qty":random.randint(2, 4)}, {"id":"leaf", "qty":1}]
            elif t == "mushroom": drops = [{"id":"mushroom", "qty":1}]
            elif t == "reed":     drops = [{"id":"reed",     "qty":random.randint(1, 3)}]
            elif t == "cactus":   drops = [{"id":"fiber",    "qty":2}]
            elif t == "flower":   drops = [{"id":"herb",     "qty":1}]
            del self.objs[(tx, ty)]
        return drops

    def add_drop(self, tx, ty, item):
        k = (tx, ty)
        self.drops.setdefault(k, [])
        for d in self.drops[k]:
            if d["id"] == item["id"]:
                d["qty"] += item["qty"]; return
        self.drops[k].append(dict(item))

    def pop_drops(self, tx, ty):
        return self.drops.pop((tx, ty), [])
