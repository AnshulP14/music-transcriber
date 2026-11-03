"""Majority vote across GAME runs: per 10 ms frame take the most common note; split notes where most runs put an onset.
Usage: vote.py OUT.csv RUN.csv..."""
import csv, sys, numpy as np

def load(f): return [(float(r['onset']), float(r['offset']), float(r['pitch'])) for r in csv.DictReader(open(f))]

def vote(files, hop=0.01):
    runs = [load(f) for f in files]; n = len(runs); L = int(max(r[-1][1] for r in runs) / hop) + 2
    P = np.full((n, L), -1); O = np.zeros((n, L))
    for i, r in enumerate(runs):
        for s, e, p in r:
            a, b = int(round(s / hop)), int(round(e / hop)); P[i, a:b] = int(round(p)); O[i, max(0, a - 3):a + 4] = 1
    need = n // 2 + 1; onset = O.sum(0) >= need; out = []; cur = None
    for t in range(L):
        v = P[:, t][P[:, t] >= 0]; p = -1
        if len(v) >= need:
            vals, cnt = np.unique(v, return_counts=True); p = int(vals[cnt.argmax()])
        new = p >= 0 and (cur is None or p != cur[2] or (onset[t] and not onset[t - 1] and t - cur[0] >= 6))
        if cur is not None and (p < 0 or new): out.append(cur); cur = None
        if p >= 0 and cur is None: cur = [t, t + 1, p]
        elif cur is not None: cur[1] = t + 1
    if cur: out.append(cur)
    return [(a * hop, b * hop, p) for a, b, p in out if (b - a) * hop >= 0.05]

if __name__ == '__main__':
    with open(sys.argv[1], 'w') as fh:
        fh.write('onset,offset,pitch\n'); fh.writelines(f'{a:.3f},{b:.3f},{p}\n' for a, b, p in vote(sys.argv[2:]))
    print(sys.argv[1])
