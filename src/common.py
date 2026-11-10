"""Shared paths, beat grid, note names, chord tables and the check-mix synth."""
import json, os, subprocess
from pathlib import Path
import numpy as np
from music21 import key, pitch

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'models'
SONG_DIR = ROOT / 'songs' / os.environ['SONG']  # set by run.sh
SOURCE, WORK, OUT = SONG_DIR / 'source', SONG_DIR / 'work', SONG_DIR / 'out'
SONG = json.load(open(SONG_DIR / 'song.json'))
SEP = WORK / 'sep'
VOCALS = SEP / 'htdemucs/song/vocals.wav'
STEM = lambda name: SEP / f'htdemucs_6s/song/{name}.wav'
BASS = WORK / 'bass.wav'  # bass stem, plus the guitar stem's low band when Demucs filed the bass under guitar (written by stems_bp.py)

SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT = ['C', 'D-', 'D', 'E-', 'E', 'F', 'G-', 'G', 'A-', 'A', 'B-', 'B']
KEY = key.Key(*SONG['key'].split())  # e.g. "B- dorian", "A minor", "E- major"
NAMES = FLAT if KEY.sharps < 0 else SHARP  # spelling that matches the key signature
pitch_name = lambda p: NAMES[p % 12] + str(p // 12 - 1)
pc_of = lambda name: pitch.Pitch(name).pitchClass


def _diatonic():  # default chord set when song.json lists none: the key's major and minor triads
    t = KEY.tonic.pitchClass; sc = sorted({p.pitchClass for p in KEY.getScale().getPitches()}, key=lambda x: (x - t) % 12); out = []
    for i, r in enumerate(sc):
        third, fifth = (sc[(i + 2) % 7] - r) % 12, (sc[(i + 4) % 7] - r) % 12
        if fifth == 7: out.append(NAMES[r] + ('m' if third == 3 else ''))
    return out


CHORDS = SONG.get('chords') or _diatonic()
CHORD_ROOT = {c: pc_of(c.rstrip('m')) for c in CHORDS}
MINOR = {c for c in CHORDS if c.endswith('m')}
MELODY_RANGE = (45, 81)


def chord_tones(c):
    r = CHORD_ROOT[c]
    return r, (r + (3 if c in MINOR else 4)) % 12, (r + 7) % 12


def load(name): return json.load(open(WORK / name))
def save(name, obj): json.dump(obj, open(WORK / name, 'w'))


class Grid:
    """Beat times from beats_chords.py; positions are 16ths counted from bar 1 beat 1."""
    def __init__(self):
        g = load('grid.json')
        self.beats, self.B0, self.bpm = np.array(g['beats']), g['B0'], round(g['bpm'])
        self.nbars, self.chords = g['nbars'], g['chords']
        self._idx = np.arange(len(self.beats))

    def to16(self, t): return int(round((np.interp(t, self.beats, self._idx) - self.B0) * 4))
    def time(self, s16): return float(np.interp(self.B0 + s16 / 4, self._idx, self.beats))


def quantize(rows, grid, fill_gaps=True):
    """(onset_s, offset_s, midi) rows -> monophonic [start16, end16, midi] on the 16th grid."""
    q = []
    for s, e, p in rows:
        a, b = grid.to16(s), grid.to16(e); b = max(b, a + 1)
        if q and a < q[-1][1]:  # overlap: previous note ends where this one starts
            if a <= q[-1][0]: a = q[-1][0] + 1
            q[-1][1] = a; b = max(b, a + 1)
        q.append([a, b, p])
    for i in range(len(q) - 1 if fill_gaps else 0):  # close gaps of a single 16th
        if 0 < q[i + 1][0] - q[i][1] <= 1: q[i][1] = q[i + 1][0]
    return [x for x in q if x[0] >= 0]


def check_mix(events, grid, mp3, harmonics, decay, attack, song_level, part_level, gain=lambda p: 1.0):
    """Synthesize (start16, end16, [midis]) events at the song's real beat times and mix them over it."""
    import librosa, soundfile as sf
    y, sr = librosa.load(WORK / 'song.wav', sr=44100, mono=True); part = np.zeros_like(y)
    for a, b, ps in events:
        s, e = grid.time(a), grid.time(b); i0 = int(s * sr); n = max(1, int((e - s) * sr) - 200); t = np.arange(n) / sr
        env = np.minimum(1, t / attack) * np.exp(-t * decay) * np.minimum(1, (n - np.arange(n)) / 400)
        for p in ps:
            f = librosa.midi_to_hz(p)
            tone = sum(h * np.sin(2 * np.pi * f * (k + 1) * t) for k, h in enumerate(harmonics)) * env * gain(p)
            part[i0:i0 + n] += tone[:max(0, len(part) - i0)]
    wav = WORK / (mp3.stem + '.wav')
    sf.write(wav, song_level * y / np.abs(y).max() + part_level * part / np.abs(part).max(), sr)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-b:a', '160k', mp3], check=True)
