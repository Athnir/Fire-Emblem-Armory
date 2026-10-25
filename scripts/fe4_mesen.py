"""
Runs Genealogy of the Holy War in Mesen 2 (headless, `--testrunner`) with a Lua script, for what the ROM alone can't show. Used to
find which unit lists each chapter's opening script loads: the game is booted, the title menu and cut scenes are pushed through with
button presses, and the chapter number in work RAM ($7E:0D6A) is set just before the chapter loads, so any chapter can be started.

    python scripts/fe4_mesen.py lists 0 11        # the lists each chapter's script loads in its first moments

Mesen 2 is at C:\\Users\\golds\\Documents\\Mesen2\\Mesen.exe (or set MESEN). Lua file access stays off: results come back on stdout.
Frame numbers: the title screen is up by about frame 700, the first chapter loads at about frame 1690.
"""
import os
import subprocess
import sys
import tempfile

from fe4_rom import ROM

MESEN = os.environ.get('MESEN', r'C:\Users\golds\Documents\Mesen2\Mesen.exe')

PRELUDE = r'''
local frame = 0
local schedule = {}
function press(a, b, keys) schedule[#schedule + 1] = {a, b, keys} end
emu.addEventCallback(function()
  local pad = {}
  for _, s in ipairs(schedule) do
    if frame >= s[1] and frame <= s[2] then for _, k in ipairs(s[3]) do pad[k] = true end end
  end
  emu.setInput(pad, 0)
end, emu.eventType.inputPolled)
'''


def run(body, timeout=900):
    """Runs a Lua script (after the prelude) and returns its stdout lines, minus Mesen's own uninitialised-memory noise."""
    with tempfile.NamedTemporaryFile('w', suffix='.lua', delete=False) as f:
        f.write(PRELUDE + body)
        path = f.name
    try:
        r = subprocess.run([MESEN, '--testrunner', ROM, path], capture_output=True, text=True, timeout=timeout)
    finally:
        os.unlink(path)
    return [l for l in r.stdout.splitlines() if 'Uninitialized' not in l]


def opening_lists(chapter, until=3200):
    """The unit lists (indexes into the table at $81:C000) that the chapter's scripts load in the first `until` frames, in order."""
    body = r'''
for f = 700, 6000, 60 do press(f, f + 3, {'a'}) end
for f = 730, 6000, 120 do press(f, f + 3, {'start'}) end
emu.addMemoryCallback(function()
  local st = emu.getState()
  print(string.format("LIST %%d %%04x", frame, st["cpu.a"] or 0))
end, emu.callbackType.exec, 0x8488EC, 0x8488EC)
emu.addEventCallback(function()
  frame = frame + 1
  if frame == 1684 then emu.write(0x0D6A, %d, emu.memType.snesWorkRam) end
  if frame >= %d then emu.stop(0) end
end, emu.eventType.endFrame)
''' % (chapter, until)
    out = []
    for line in run(body):
        if line.startswith('LIST'):
            _, frame, pointer = line.split()
            out.append((int(frame), (int(pointer, 16) - 0xC000)))
    return out


if __name__ == '__main__':
    if sys.argv[1:2] == ['lists']:
        from fe4_rom import u16
        first, last = int(sys.argv[2]), int(sys.argv[3])
        offsets = [u16(0x1C000 + 2 * i) for i in range(58)]
        for c in range(first, last + 1):
            lists = [offsets.index(p) for _, p in opening_lists(c)]
            print(c, lists)
