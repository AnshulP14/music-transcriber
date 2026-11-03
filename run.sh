#!/usr/bin/env bash
# Usage: ./run.sh SONG            rebuild the score from what is already in songs/SONG/work (fast, deterministic)
#        ./run.sh SONG all        rerun everything from songs/SONG/source/song.* (slow; GAME is random, so the melody can change)
#        ./run.sh SONG <stage>    one stage: audio stems beats game melody accomp score check
set -euo pipefail
cd "$(dirname "$0")"
export SONG=${1:?usage: ./run.sh SONG [stage]}
R=$PWD; S=songs/$SONG; W=$S/work; PY=$R/.venv/bin/python; GAME_RUNS=${GAME_RUNS:-7}
[ -f "$S/song.json" ] || { echo "missing $S/song.json (see README)" >&2; exit 1; }
mkdir -p "$W" "$S/out"

audio()  { ffmpeg -loglevel error -y -i "$(ls "$S"/source/song.* | head -1)" -ar 44100 "$W/song.wav"; }
stems()  {
  $PY -m demucs -n htdemucs --two-stems=vocals -d mps -o "$W/sep" "$W/song.wav"
  $PY -m demucs -n htdemucs_6s -d mps -o "$W/sep" "$W/song.wav"
  .venv-sep/bin/audio-separator "$W/sep/htdemucs/song/vocals.wav" -m mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt \
    --model_file_dir models/separator --output_dir "$W/sep/kara" --output_format WAV \
    --custom_output_names '{"Vocals": "lead", "Instrumental": "backing"}'
  $PY src/stems_bp.py || echo "stems_bp.py needs basic-pitch (Python 3.11 env); keeping the existing $W/stems_bp.json" >&2
}
beats()  { $PY src/beats_chords.py; }
game()   {  # GAME_RUNS runs per voice: the full vocal, the lead-only and the backing-only karaoke tracks
  local lang; lang=$($PY -c "import json; print(json.load(open('$S/song.json')).get('language', 'en'))")
  for src in orig:sep/htdemucs/song/vocals.wav lead:sep/kara/lead.wav back:sep/kara/backing.wav; do
    for i in $(seq 1 "$GAME_RUNS"); do
      d=$R/$W/game/${src%%:*}_$i; mkdir -p "$d"
      (cd models/GAME && "$PY" infer.py extract "$R/$W/${src#*:}" -m "$R/models/GAME-1.0-medium/model.pt" -l "$lang" \
        --output-formats csv --pitch-format number --output-dir "$d" >/dev/null 2>&1)
    done
  done
}
melody() {
  mkdir -p "$W/runs"
  for d in "$W"/game/orig_*; do $PY src/game_to_grid.py "$d"/*.csv "$W/runs/$(basename "$d").json"; done
  $PY src/vote.py "$W/game/vote_lead.csv" "$W"/game/lead_*/*.csv
  $PY src/vote.py "$W/game/vote_back.csv" "$W"/game/back_*/*.csv
  $PY src/medoid.py "$W"/runs/*.json
  $PY src/duet.py
}
accomp() { $PY src/accomp.py; }
score()  { $PY src/build_score.py; $PY src/make_html.py; }
check()  { [ -f "$S/source/reference.json" ] && $PY src/refcheck.py; $PY src/check_vocals.py; }

case "${2:-build}" in
  build) melody; accomp; score ;;
  all)   audio; stems; beats; game; melody; accomp; score; check ;;
  *)     "$2" ;;
esac
