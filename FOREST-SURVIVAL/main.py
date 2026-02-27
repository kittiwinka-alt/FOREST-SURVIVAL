"""
╔══════════════════════════════════════════╗
║   🌲  FOREST SURVIVAL  v3.0  🌲          ║
║   Python 3.8+  |  pip install pygame     ║
║   python main.py                         ║
╚══════════════════════════════════════════╝

โครงสร้างไฟล์:
  main.py      — จุดเริ่มต้น
  config.py    — ค่าคงที่และข้อมูลเกม
  audio.py     — ระบบเสียง (procedural)
  world.py     — สร้างโลกและ tile rendering
  entities.py  — PS, Enemy, Player
  renderer.py  — วาด objects ในโลก
  ui.py        — HUD, screens, overlays
  game.py      — Game loop หลัก
"""

from game import Game


if __name__ == "__main__":
    game = Game()
    game.run()
