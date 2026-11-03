"""Beat grid, downbeat, bar 1 and a first chord guess per half bar -> work/grid.json."""
import numpy as np, librosa, warnings; warnings.filterwarnings('ignore')
from common import WORK, SEP, VOCALS, STEM, SONG, CHORDS, CHORD_ROOT, chord_tones, save

SR, HOP = 22050, 512
y, _ = librosa.load(WORK / 'song.wav', sr=SR)
_, bt = librosa.beat.beat_track(onset_envelope=librosa.onset.onset_strength(y=y, sr=SR), sr=SR, units='time', tightness=400, start_bpm=SONG.get('bpm_hint', 120))
p0, p1 = bt[1] - bt[0], bt[-1] - bt[-2]
beats = np.concatenate([bt[0] - p0 * np.arange(8, 0, -1), bt, bt[-1] + p1 * np.arange(1, 9)])  # pad 8 beats each side
bidx = lambda t: np.interp(t, beats, np.arange(len(beats)))
bpm = 60 / np.median(np.diff(bt))

# accompaniment chroma per beat (full + bass band)
yh = librosa.effects.harmonic(librosa.load(SEP / 'htdemucs/song/no_vocals.wav', sr=SR)[0])
ch = librosa.feature.chroma_cqt(y=yh, sr=SR, hop_length=HOP)
bass = librosa.feature.chroma_cqt(y=yh, sr=SR, hop_length=HOP, fmin=librosa.note_to_hz('C1'), n_octaves=2)
bf = librosa.time_to_frames(beats, sr=SR, hop_length=HOP)
def seg(M, a, b):
    fa, fb = bf[a], max(bf[b], bf[a] + 1); return M[:, fa:fb].mean(1) if fb <= M.shape[1] else np.zeros(12)
C = np.array([seg(ch, i, i + 1) for i in range(len(beats) - 1)]); Bs = np.array([seg(bass, i, i + 1) for i in range(len(beats) - 1)])

# downbeat phase: the kick lands hardest on beat 1 (chord-change novelty proved unstable across stem re-renders)
yd = librosa.load(STEM('drums'), sr=SR)[0]; X = np.abs(librosa.stft(yd, n_fft=1024, hop_length=256)); fq = librosa.fft_frequencies(sr=SR, n_fft=1024)
kick = librosa.onset.onset_strength(S=librosa.amplitude_to_db(X[(fq >= 30) & (fq < 120)]), sr=SR, hop_length=256)
kf = librosa.time_to_frames(beats, sr=SR, hop_length=256)
hit = np.array([kick[max(0, f - 3):f + 4].max() if 0 <= f < len(kick) else 0 for f in kf])
ph = int(np.argmax([hit[k::4].mean() for k in range(4)]))

# bar 1 = the bar holding the first sung note; the score ends with the last one
r = librosa.feature.rms(y=librosa.load(VOCALS, sr=SR)[0])[0]
sung = librosa.times_like(r, sr=SR)[20 * np.log10(r / r.max() + 1e-9) > -30]
B0 = ph + 4 * int(np.floor((bidx(sung[0]) - ph) / 4))
nbars = int(np.ceil((bidx(sung[-1]) - B0) / 4))

# chords per half bar: Viterbi over the diatonic set
def tpl(c):
    t = np.zeros(12); r_, th, fi = chord_tones(c); t[r_] = 1.2; t[th] = 1; t[fi] = 1; return t / np.linalg.norm(t)
Tm = np.array([tpl(c) for c in CHORDS])
prior = np.array(SONG.get('chord_prior') or [.15] + [0] * (len(CHORDS) - 1))  # default: lean towards the tonic chord
H = nbars * 2; E = np.zeros((H, len(CHORDS)))
for h in range(H):
    a = B0 + 2 * h; c = C[a:a + 2].mean(0); b = Bs[a:a + 2].mean(0)
    E[h] = Tm @ (c / (np.linalg.norm(c) + 1e-9)) + 0.35 * (b / (b.max() + 1e-9))[[CHORD_ROOT[x] for x in CHORDS]] + prior
V = E[0].copy(); bp = np.zeros((H, len(CHORDS)), int)
for h in range(1, H):
    M = V[:, None] + 0.12 * np.eye(len(CHORDS)); bp[h] = M.argmax(0); V = M.max(0) + E[h]
path = [int(V.argmax())]
for h in range(H - 1, 0, -1): path.append(bp[h][path[-1]])
chords = [CHORDS[i] for i in path[::-1]]

save('grid.json', {'beats': beats.tolist(), 'B0': B0, 'bpm': bpm, 'nbars': nbars, 'chords': chords})
print(f'bpm {bpm:.1f}  bars {nbars}  bar 1 at {beats[B0]:.2f}s  first chords {chords[:8]}')
