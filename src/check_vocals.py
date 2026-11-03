"""How well the melody covers the sung pitch (pyin on the vocal stem). Diagnostic only."""
import numpy as np, librosa, warnings; warnings.filterwarnings('ignore')
from common import VOCALS, Grid, load

grid = Grid(); q = load('melody.json')['q']
y, _ = librosa.load(VOCALS, sr=22050)
f0, voiced, _ = librosa.pyin(y, fmin=80, fmax=1000, sr=22050, hop_length=512)
t = librosa.times_like(f0, sr=22050, hop_length=512); sung = librosa.hz_to_midi(f0); ours = np.full(len(t), np.nan)
for a, b, p in q: ours[(t >= grid.time(a)) & (t < grid.time(b))] = p
both = voiced & np.isfinite(ours) & np.isfinite(sung)
d = np.abs(sung[both] - ours[both]); pc = np.minimum(d % 12, 12 - d % 12)
print('voiced frames covered by a note: %.0f%%' % (100 * both.sum() / max(1, voiced.sum())))
print('exact pitch (±0.5 st): %.0f%%   right note ignoring octave: %.0f%%' % (100 * np.mean(d <= .5), 100 * np.mean(pc <= .5)))
