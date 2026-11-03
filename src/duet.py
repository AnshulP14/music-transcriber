"""Bars where two voices sing different notes: the top staff follows one voice, the other goes to a 2nd-voice staff.
Reads melody_consensus.json and the lead/backing vote CSVs -> work/melody.json."""
import numpy as np
from common import WORK, SONG, Grid, load, save
from game_to_grid import read

grid = Grid(); T = load('melody_consensus.json')
V = {k: read(WORK / f'game/vote_{k}.csv', grid, fill_gaps=False)[0] for k in ('lead', 'back')}
def roll(q):
    r = np.full(grid.nbars * 16, -1)
    for a, b, p in q: r[a:b] = p
    return r
RL, RB = roll(V['lead']), roll(V['back'])
both = (RL >= 0) & (RB >= 0) & (RL != RB)
duet = [b for b in range(grid.nbars) if both[b * 16:b * 16 + 16].sum() >= 4]
inbar = lambda q, b: [n for n in q if n[0] // 16 == b]
mel = [n for n in T['q'] if n[0] // 16 not in duet]; sec = []
def top_voice(bar):  # song.json duet_top: [{from_bar, voice}, ...]; default the lead singer
    rules = [r for r in SONG.get('duet_top', []) if bar >= r['from_bar']]
    return max(rules, key=lambda r: r['from_bar'])['voice'] if rules else 'lead'
for b in duet:
    top = top_voice(b + 1); other = 'lead' if top == 'back' else 'back'
    mel += inbar(V[top], b); sec += inbar(V[other], b)
save('melody.json', {'q': sorted(mel), 'q2': sorted(sec), 'duet': [b + 1 for b in duet]})
print('duet bars', [b + 1 for b in duet], '| melody notes', len(mel), '| 2nd-voice notes', len(sec))
