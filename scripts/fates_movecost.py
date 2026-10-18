"""The game's movement-cost table (GameData.bin): cost-class column x movement-type row."""
from fates_lz import decompress

TABLE = 0x1E328  # 16 rows x 16 bytes; 0xFF = can't enter
# Rows matched to the wiki's movement groups by their woods / waste / river columns.
ROWS = {
    'Infantry A': [5], 'Infantry B': [1], 'Infantry C': [3], 'Infantry D': [4], 'Armor': [7],
    'Cavalry A': [13], 'Cavalry B': [14], 'Mages': [9], 'Beasts': [11, 12], 'Fliers': [15],
}


def load(path):
    d = decompress(open(path, 'rb').read())
    rows = [d[TABLE + r * 16:TABLE + r * 16 + 16] for r in range(16)]

    def costs(col):
        out = {}
        for group, rs in ROWS.items():
            vals = [None if rows[r][col] == 0xFF else rows[r][col] for r in rs]
            out[group] = vals[0] if len(set(vals)) == 1 else '/'.join('-' if v is None else str(v) for v in vals)
        return out
    return costs
