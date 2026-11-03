"""Score melody variants against the reference phrases (note letters, songs/SONG/source/reference.json), aligned in song order.
Usage: refcheck.py [VARIANT.json...] [--show NAME...]   (default: work/runs/*.json and work/melody.json)"""
import json, sys
from pathlib import Path
from common import SOURCE, WORK, SHARP

ref = [[SHARP.index(x[:-1]) for x in ph] for ph in json.load(open(SOURCE / 'reference.json'))]

def local(a, b):
    """Smith-Waterman: best local alignment of reference phrase a inside sequence b -> (start_j, end_j, ops)."""
    H = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]; P = [[None] * (len(b) + 1) for _ in range(len(a) + 1)]; best = (0, 0, 0)
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            v, p = max([(0, None), (H[i - 1][j - 1] + (2 if a[i - 1] == b[j - 1] else -1), 'd'), (H[i - 1][j] - 1, 'u'), (H[i][j - 1] - 1, 'l')], key=lambda t: t[0])
            H[i][j] = v; P[i][j] = p
            if v > best[0]: best = (v, i, j)
    _, i, j = best; jend = j; ops = []
    while i > 0 and j > 0 and P[i][j]:
        p = P[i][j]
        if p == 'd': ops.append(('=' if a[i - 1] == b[j - 1] else 'x', a[i - 1], b[j - 1])); i -= 1; j -= 1
        elif p == 'u': ops.append(('-', a[i - 1], None)); i -= 1
        else: ops.append(('+', None, b[j - 1])); j -= 1
    return j, jend, [('-', x, None) for x in a[:i]] + ops[::-1]

def ordered(q):
    seq = [p % 12 for a, b, p in q]; pos = tot = n = exact = 0; out = []
    for k, ph in enumerate(ref):
        j0, j1, ops = local(ph, seq[pos:pos + 60])
        ops += [('-', x, None) for x in ph[sum(o[0] != '+' for o in ops):]]  # reference tail left unaligned
        errs = sum(o[0] != '=' for o in ops)
        tot += len(ops) - errs; n += len(ph); exact += errs == 0
        out.append((k + 1, q[min(pos + j0, len(q) - 1)][0] // 16 + 1, errs, ops)); pos += j1
    return tot / n, exact, out

if __name__ == '__main__':
    args = sys.argv[1:]; cut = args.index('--show') if '--show' in args else len(args); show = args[cut + 1:]
    files = [Path(f) for f in args[:cut]] or sorted((WORK / 'runs').glob('*.json')) + [WORK / 'melody.json']
    res = sorted(((*ordered(json.load(open(f))['q']), f.stem) for f in files), key=lambda r: -r[0])
    print(f"{'variant':16s} matched  exact phrases (in song order)")
    for a, e, o, name in res: print(f'{name:16s} {a * 100:5.1f}%   {e}/{len(ref)}')
    for a, e, o, name in res:
        if name not in show: continue
        print(f'\n{name}: phrases that differ from the reference')
        for k, bar, errs, ops in o:
            if errs:
                d = [f'missing {SHARP[r]}' if t == '-' else f'extra {SHARP[u]}' if t == '+' else f'{SHARP[r]}→{SHARP[u]}' for t, r, u in ops if t != '=']
                print(f'  phrase {k:2d} (bar {bar:2d}): ' + ', '.join(d))
