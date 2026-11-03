"""GAME note CSV -> [start16, end16, midi] notes on the beat grid. Usage: game_to_grid.py RUN.csv OUT.json"""
import csv, sys, json, numpy as np
from common import Grid, MELODY_RANGE, quantize

def read(path, grid, fill_gaps=True):
    rows = [(float(r['onset']), float(r['offset']), float(r['pitch'])) for r in csv.DictReader(open(path))]
    dev = np.median([p - round(p) for s, e, p in rows if e - s > 0.2]) if rows else 0.0  # recording's tuning offset
    lo, hi = MELODY_RANGE
    return quantize([(s, e, int(round(p - dev))) for s, e, p in rows if lo <= round(p - dev) <= hi], grid, fill_gaps), dev

if __name__ == '__main__':
    q, dev = read(sys.argv[1], Grid())
    json.dump({'q': q}, open(sys.argv[2], 'w'))
    print(sys.argv[2], f'tuning offset {dev:.2f} st, {len(q)} notes')
