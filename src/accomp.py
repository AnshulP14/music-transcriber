"""Clean bass line + chords refined by the bass roots -> work/accomp.json, and a multi-track MIDI of every part."""
import numpy as np, librosa, pretty_midi, warnings; warnings.filterwarnings('ignore')
from common import OUT, STEM, CHORDS, CHORD_ROOT, Grid, load, save

grid = Grid(); S = load('stems_bp.json'); q = load('melody.json')['q']; old = grid.chords; H = len(old)
# bass: real bass range only, octave pairs -> lower, monophonic, 16th grid
by = {}
for s, e, p, v in S['bass']:
    if v < 0.3 or not 28 <= p <= 52 or e - s < 0.08: continue
    a, b = grid.to16(s), grid.to16(e)
    if not 0 <= a < grid.nbars * 16: continue
    if a in by:  # same onset: keep lower (upper is usually the octave overtone) unless much quieter
        pa, _, pv = by[a]
        if p < pa and v >= 0.5 * pv or v > 2 * pv: by[a] = (p, max(b, a + 1), v)
    else: by[a] = (p, max(b, a + 1), v)
ons = sorted(by); bass = []
for i, a in enumerate(ons):
    p, b, _ = by[a]; nxt = ons[i + 1] if i + 1 < len(ons) else a + 8
    b = min(max(b, a + 1), nxt, a + 8)
    if bass and bass[-1][2] == p and bass[-1][1] >= a and a % 4: bass[-1][1] = b; continue  # merge repeated off-beat 16ths
    bass.append([a, b, p])
# chords: the chroma choice, re-scored with bass-stem root evidence
chords = []; changed = []
for h in range(H):
    w = np.zeros(12)
    for a, b, p in bass:
        o = min(b, h * 8 + 8) - max(a, h * 8)
        if o > 0 and p < 48: w[p % 12] += o * (2 if a == h * 8 else 1)  # note on the half-bar downbeat counts double
    c = old[h]
    if w.sum() >= 3:
        r = int(w.argmax())
        early = {p % 12 for a, b, p in bass if h * 8 - 1 <= a < h * 8 + 4}  # root must sound in the first beat (or as a push into it)
        if w[r] >= 0.5 * w.sum() and r != CHORD_ROOT[c] and r in early:
            cand = [n for n in CHORDS if CHORD_ROOT[n] == r]  # first listed chord on that root
            if cand: c = cand[0]; changed.append((h // 2 + 1, (h % 2) * 2 + 1, old[h], c))
    chords.append(c)
print('bass notes', len(bass), '| chords changed by bass:', len(changed))
for x in changed: print('  bar %d beat %d: %s -> %s' % x)
save('accomp.json', {'bass': bass, 'chords': chords})

# multi-track MIDI of every part (raw stems quantized onto the beat grid)
spb = 60 / grid.bpm; pm = pretty_midi.PrettyMIDI(initial_tempo=grid.bpm)
def track(name, prog, notes, drum=False):
    i = pretty_midi.Instrument(program=prog, name=name, is_drum=drum)
    for a, b, p, *v in notes:
        i.notes.append(pretty_midi.Note(velocity=int(v[0]) if v else 90, pitch=int(p), start=a / 4 * spb, end=max(b, a + 1) / 4 * spb))
    pm.instruments.append(i)
track('Vocal melody', 73, q)
track('Bass', 33, bass)
for nm, prog, label in [('guitar', 25, 'Guitar'), ('other', 49, 'Other (keys/strings/synth)')]:
    track(label, prog, [(grid.to16(s), grid.to16(e), p, int(40 + 80 * min(1, v))) for s, e, p, v in S[nm] if v >= 0.35 and grid.to16(s) >= 0])
y, sr = librosa.load(STEM('drums'), sr=22050)
X = np.abs(librosa.stft(y, n_fft=1024, hop_length=256)); f = librosa.fft_frequencies(sr=sr, n_fft=1024); dr = set()
for gm, (lo, hi) in {36: (30, 120), 38: (150, 400), 42: (6000, 11000)}.items():  # kick, snare, hi-hat by frequency band
    env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(X[(f >= lo) & (f < hi)]), sr=sr, hop_length=256)
    for t in librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=256, units='time', delta=0.3):
        if (k := grid.to16(t)) >= 0: dr.add((k, k + 1, gm, 90))
track('Drums (approx.)', 0, sorted(dr), drum=True)
pm.write(str(OUT / 'all_parts.mid'))
print('tracks', [(i.name, len(i.notes)) for i in pm.instruments])
