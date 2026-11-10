"""basic-pitch notes for the bass / guitar / other / piano stems -> work/stems_bp.json. Needs basic-pitch (Python 3.11 env)."""
import json, warnings; warnings.filterwarnings('ignore')
import numpy as np, librosa, soundfile as sf
from scipy.signal import butter, sosfiltfilt
from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
from common import STEM, BASS, save

# Demucs sometimes files a distorted or mid-heavy bass under "guitar". If the guitar stem has far more low end
# than the bass stem, add its low band (< 250 Hz) to the bass.
yb, sr = librosa.load(STEM('bass'), sr=None)
yg, _ = librosa.load(STEM('guitar'), sr=sr)
sos = butter(4, 250, 'low', fs=sr, output='sos'); gl = sosfiltfilt(sos, yg)
eb, eg = float(np.sum(sosfiltfilt(sos, yb) ** 2)), float(np.sum(gl ** 2))
print(f'low-band energy bass {eb:.3g}, guitar {eg:.3g}')
if eg > 3 * eb: yb = yb + gl; print('bass: adding the low-passed guitar stem')
sf.write(BASS, yb, sr)

cfg = {'bass': dict(minimum_frequency=30, maximum_frequency=300, melodia_trick=True),
       'guitar': dict(minimum_frequency=70, maximum_frequency=1500, melodia_trick=False),
       'other': dict(minimum_frequency=60, maximum_frequency=2000, melodia_trick=False),
       'piano': dict(minimum_frequency=27, maximum_frequency=4200, melodia_trick=False)}
out = {}
for s, c in cfg.items():
    _, _, notes = predict(str(BASS if s == 'bass' else STEM(s)), ICASSP_2022_MODEL_PATH, onset_threshold=0.5, frame_threshold=0.3, minimum_note_length=80, **c)
    out[s] = sorted((float(a), float(b), int(p), float(v)) for a, b, p, v, *_ in notes); print(s, len(out[s]))
save('stems_bp.json', out)
