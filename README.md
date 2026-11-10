# music-transcriber

Turns a song recording into a piano score you can play along with. The output is a web page (`out/score.html`) showing:

- the sung melody, plus a 2nd-voice staff wherever two singers overlap;
- a two-hand piano part built from the song's real bass line and chords;
- a key name under every melody note;
- playback that highlights notes as the song plays, and a metronome.

It also writes MusicXML, MIDI (score + every instrument), a note-by-note CSV with an empty lyrics column, and check mixes (the song with the transcription beeped over it).

## Songs

Each song lives in its own folder, which stays on your machine and is gitignored:

```
songs/<name>/
  song.json            settings (copy songs/example/song.json)
  source/song.mp3      the recording (any format ffmpeg reads, named song.*)
  source/reference.json  optional: reference phrases (lists of note names like "A#4") for refcheck.py
  work/                stems, GAME runs, intermediate JSON
  out/                 score.html, score.musicxml, score.mid, all_parts.mid, check mixes, lyrics_alignment.csv
```

`song.json` fields:

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | Song title shown on the page |
| `artist` | yes | Artist shown on the page |
| `key` | yes | music21 key string, e.g. `"A minor"`, `"E- major"`, `"B- dorian"`. Sets the key signature and spelling. |
| `chords` | no | Chord names allowed in the chord detection, e.g. `["Am", "C", "G"]`. Default: the key's major and minor triads. |
| `chord_prior` | no | Bias for each chord in `chords`. Default: a slight lean towards the first chord. |
| `bpm_hint` | no | Starting tempo guess for the beat tracker |
| `language` | no | GAME language code (default `en`) |
| `duet_top` | no | Which voice goes on the top staff where two voices overlap, e.g. `[{"from_bar": 44, "voice": "back"}]`. Default: `lead`. |
| `notes` | no | Extra lines (HTML) for the page's "How to read this" box |

## Run

```bash
./run.sh <name> fetch "song title artist"
./run.sh <name> all
```

`fetch` downloads the first YouTube match (or a URL you pass) with yt-dlp into `source/song.mp3`. Downloading from YouTube goes against its terms, so you can drop in your own file instead. `all` runs everything from the recording. Other forms:

- `./run.sh <name>` rebuilds the score from `work/` in about a minute.
- `./run.sh <name> <stage>` runs one stage: `audio` `stems` `beats` `game` `melody` `accomp` `score` `check`.

## Stages

1. **audio, stems:**
   - Demucs splits off the vocals and six instrument stems;
   - a karaoke model splits the vocals into lead and backing;
   - basic-pitch transcribes the instrument stems.
2. **beats:** `beats_chords.py` finds the beat grid, the downbeat (from the kick drum), bar 1, and a first chord guess per half bar.
3. **game:** GAME (openvpi, singing-to-MIDI) runs `GAME_RUNS` times (default 7) on each vocal track. Its output varies from run to run.
4. **melody:**
   - `game_to_grid.py` snaps each run to 16th notes;
   - `medoid.py` keeps the run that agrees most with the others (it never looks at a reference);
   - `duet.py` puts one voice on a 2nd-voice staff in bars where lead and backing sing different notes.
5. **accomp:** `accomp.py` cleans the bass line, corrects chords where the bass root disagrees, and writes `all_parts.mid`.
6. **score:**
   - `build_score.py` writes the score files, the CSV and the check mixes;
   - `make_html.py` writes the page.
7. **check:**
   - `refcheck.py` scores melodies against `reference.json`, if there is one;
   - `check_vocals.py` measures how much of the sung pitch the melody covers.

## Setup

- **ffmpeg** must be installed.
- **`.venv`** (Python 3.12) runs the pipeline:

  ```bash
  pip install -r requirements.txt -r models/GAME/requirements.txt
  ```

- **`.venv-sep`** (Python 3.12) runs the karaoke split:

  ```bash
  pip install "audio-separator[cpu]" audioread
  ```

- **`.venv-bp`** (Python 3.11) runs basic-pitch for `stems_bp.py`:

  ```bash
  pip install basic-pitch music21 "setuptools<81"
  ```

Models go in `models/` (gitignored):

- `models/GAME`: a clone of https://github.com/openvpi/GAME.
- `models/GAME-1.0-medium/model.pt`: from that repo's v1.0.0 release.
- `models/separator/`: audio-separator downloads `mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt` (870 MB) here on first use.

Lyrics are never included. The CSV has an empty `syllable` column for you to fill in.
