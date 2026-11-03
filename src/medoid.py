"""Pick the GAME run that agrees most with all the others (no reference used) -> work/melody_consensus.json.
Usage: medoid.py RUN.json..."""
import json, shutil, sys, numpy as np
from common import WORK

fs = sys.argv[1:]; Q = [json.load(open(f))['q'] for f in fs]; L = max(q[-1][1] for q in Q) + 1
def roll(q):
    r = np.full(L, -1); on = np.zeros(L, bool)
    for a, b, p in q: r[a:b] = p; on[a] = True
    return r, on
R = [roll(q) for q in Q]
def agree(x, y):
    (r1, o1), (r2, o2) = x, y; v = (r1 >= 0) | (r2 >= 0)
    return 0.7 * np.mean(r1[v] == r2[v]) + 0.3 * np.sum(o1 & o2) / max(1, np.sum(o1 | o2))
S = [np.mean([agree(R[i], R[j]) for j in range(len(R)) if j != i]) for i in range(len(R))]
for f, s in sorted(zip(fs, S), key=lambda t: -t[1]): print(f'{s:.3f} {f}')
shutil.copy(fs[int(np.argmax(S))], WORK / 'melody_consensus.json')
