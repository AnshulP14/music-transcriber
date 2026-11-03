"""Score (melody, 2nd voice, piano RH/LH) as MusicXML + MIDI, the note-by-note CSV and the two check mixes -> out/."""
import csv, numpy as np, librosa, warnings; warnings.filterwarnings('ignore')
from music21 import stream, note, chord, meter, key, tempo, metadata, harmony, clef, layout
from common import OUT, STEM, SONG, KEY, SHARP, CHORD_ROOT, Grid, chord_tones, pitch_name, load, check_mix

grid = Grid(); M = load('melody.json'); q = M['q']; A = load('accomp.json'); bass, chords = A['bass'], A['chords']; nbars = grid.nbars
triad = lambda c: sorted(65 + ((pc - 65) % 12) for pc in chord_tones(c))  # close voicing around F4-E5, so hands barely move
low = lambda pc: 39 + ((pc - 39) % 12)  # bass register D#2-D3

# bars where the bass really plays (within 20 dB of its loudest bar) get the groove; quiet bars get held chords
yb, _ = librosa.load(STEM('bass'), sr=22050)
rms = [float(np.sqrt(np.mean(yb[int(grid.time(16 * b) * 22050):int(grid.time(16 * b + 16) * 22050)] ** 2))) for b in range(nbars)]
band = [rms[b] >= max(rms) * 0.1 and sum(b * 16 <= a < b * 16 + 16 for a, _, _ in bass) >= 2 for b in range(nbars)]
print('quiet bars', [b + 1 for b in range(nbars) if not band[b]])

rh, lh = [], []  # events: (start16, end16, [midis])
for bar in range(nbars):
    o = bar * 16; c1, c2 = chords[2 * bar], chords[2 * bar + 1]
    if band[bar]:  # RH hits on 1, 2-a (pushes into the beat-3 chord), 4 — where the bass and kick land
        rh += [(o, o + 7, triad(c1)), (o + 7, o + 12, triad(c2)), (o + 12, o + 16, triad(c2))]
        hits = {}  # LH: real bass rhythm on an 8th grid (+ the 2-a / 4-a pushes), held to the next note
        for a, _, p in bass:
            if not o <= a < o + 16: continue
            k = a - o
            if k % 2 and k not in (7, 15): k -= 1  # 'e'/'a' 16ths -> the 8th before, except pushes
            hits.setdefault(k, low(p))
        ks = sorted(hits); ks = [k for i, k in enumerate(ks) if i == 0 or hits[k] != hits[ks[i - 1]] or k in (0, 7, 8, 12)]
        lh += [(o + k, o + (ks[i + 1] if i + 1 < len(ks) else 16), [hits[k]]) for i, k in enumerate(ks)]
    else:
        rh += [(o, o + 8, triad(c1)), (o + 8, o + 16, triad(c2))]
        lh += [(o + 8 * h, o + 8 * h + 8, [low(CHORD_ROOT[c])]) for h, c in enumerate((c1, c2))]

def part(events, cl, name, labels=False):
    p = stream.Part(); p.partName = name
    for x in (cl, key.KeySignature(KEY.sharps), meter.TimeSignature('4/4')): p.append(x)
    cur = 0
    for a, b, ps in sorted(events):
        a = max(a, cur)
        if b <= a: continue
        if a > cur: r = note.Rest(); r.quarterLength = (a - cur) / 4; p.append(r)
        n = note.Note(pitch_name(ps[0])) if len(ps) == 1 else chord.Chord([pitch_name(x) for x in ps])
        n.quarterLength = (b - a) / 4
        if labels: n.lyric = SHARP[ps[0] % 12]  # key name under each note
        p.append(n); cur = b
    if cur < nbars * 16: r = note.Rest(); r.quarterLength = (nbars * 16 - cur) / 4; p.append(r)
    m = p.makeMeasures(); m.makeTies(inPlace=True); return m

up = lambda notes: [(a, b, [p + 12]) for a, b, p in notes]  # melody written an octave above sung pitch
pm = part(up(q), clef.TrebleClef(), 'Melody', True); pm.measure(1).insert(0, tempo.MetronomeMark(number=grid.bpm))
p2 = part(up(M['q2']), clef.TrebleClef(), '2nd voice', True) if M['q2'] else None
pr, pl = part(rh, clef.TrebleClef(), 'Piano RH'), part(lh, clef.BassClef(), 'Piano LH')
prev = None
for h, c in enumerate(chords):
    if c != prev: pm.measure(h // 2 + 1).insert((h % 2) * 2, harmony.ChordSymbol(c)); prev = c
sc = stream.Score(); sc.metadata = metadata.Metadata(title=SONG['title'], composer=SONG.get('artist', '') + ' — auto-transcribed')
for x in [pm, p2, pr, pl]:
    if x: sc.insert(0, x)
sc.insert(0, layout.StaffGroup([pr, pl], symbol='brace'))
sc.write('musicxml', OUT / 'score.musicxml'); sc.write('midi', OUT / 'score.mid')

# note-by-note sheet, with an empty syllable column for lyrics
count = ['', 'e', '&', 'a']
with open(OUT / 'lyrics_alignment.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['note', 'bar', 'count', 'key', 'piano_key', 'length_beats', 'time_s', 'syllable'])
    for i, (a, b, p) in enumerate(q):
        w.writerow([i + 1, a // 16 + 1, f'{(a % 16) // 4 + 1}{count[a % 4]}', SHARP[p % 12], SHARP[p % 12] + str((p + 12) // 12 - 1), (b - a) / 4, round(grid.time(a), 2), ''])

check_mix(up(q), grid, OUT / 'check_mix.mp3', harmonics=(1, .3), decay=1.5, attack=.01, song_level=.55, part_level=.35)
check_mix(rh + lh, grid, OUT / 'check_accompaniment.mp3', harmonics=(1, .4, .15), decay=2.5, attack=.005, song_level=.5, part_level=.4,
          gain=lambda p: 1.3 if p < 55 else 0.6)
print('bars', nbars, '| band bars', sum(band), '| melody', len(q), '| rh', len(rh), '| lh', len(lh))
