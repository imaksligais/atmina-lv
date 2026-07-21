# Video ingest — vienreizējais setup

## 1. ffmpeg

yt-dlp un pydub atkarība.

**Windows:**
```powershell
winget install --id=Gyan.FFmpeg
# vai
choco install ffmpeg
```

**macOS / Linux:** `brew install ffmpeg` / pakotņu menedžeris.

Verificē:
```bash
ffmpeg -version
```

## 2. HuggingFace token

pyannote (4.x, `speaker-diarization-community-1`) prasa autentifikāciju.

1. Akceptē lietošanas noteikumus uz https://huggingface.co/pyannote/speaker-diarization-community-1
2. Ģenerē tokenu: https://huggingface.co/settings/tokens (read access pietiek)
3. Saglabā:

```bash
# Variants A — fails (preferred, gitignored)
mkdir -p data
echo '{"token": "hf_yourtoken"}' > data/hf_token.json

# Variants B — env var
export HUGGINGFACE_TOKEN=hf_yourtoken
```

## 3. CUDA / GPU

```bash
.venv/Scripts/python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

Bez GPU viss strādā (noklusējums), tikai lēnāk (ASR ~2.3× reāllaiks uz CPU).

**Uz datora ar GPU:**
- **Diarizācija** GPU paņem automātiski, ja `torch.cuda.is_available()` (pyannote caur torch — droši).
- **ASR** GPU ir apzināts opt-in: `VIDEO_INGEST_DEVICE=cuda` (ctranslate2 ar nesaderīgu cuDNN nokrīt ar exit 127, tāpēc auto-detekcijas nav). ctranslate2 4.8.x = CUDA 12 + cuDNN 9 būve.
- `VIDEO_INGEST_DEVICE` ietekmē ABAS stадijas: `cuda` / `cpu` / nesetots (= ASR cpu, diarize auto).
- **Windows GPU:** PyPI `torch==2.13.0` ir CPU-only wheel — CUDA būvei instalē no `https://download.pytorch.org/whl/cu126` indeksa (Linux PyPI torch CUDA nāk līdzi pēc noklusējuma).

**Darbs no cita datora (GPU kaste ↔ galvenā mašīna):** smagās stadijas (fetch/ASR/diarize/align) ir tīri failu-bāzētas — visi artefakti dzīvo `.scratch/videos/<slug>/`. Var palaist `fetch` uz GPU kastes, pārkopēt darbvietas mapi uz galveno mašīnu un tur izpildīt `finalize` (tas vienīgais raksta DB). Vienreizējais setup uz jaunās mašīnas: ffmpeg (§1), HF tokens (§2 — `data/hf_token.json` ir gitignored, jāpārnes ar roku vai env var; gate akcepts ir konta līmenī, atkārtoti nav jāakceptē).

## 4. Pirmā palaišana

Pirmā `python -m src.video_ingest fetch ...` lejupielādēs:
- faster-whisper large-v3 INT8 (~1.6 GB) → `~/.cache/whisper/`
- pyannote/speaker-diarization-community-1 → `~/.cache/huggingface/`

Pēc tam ātri.

**NB (Windows):** `speechbrain` NEDRĪKST būt instalēts venv (skat. piezīmi `requirements.txt`), un torchcodec FFmpeg-shared-DLL prasība ir apieta kodā — `diarize.py` padod pipeline'am jau dekodētu waveform caur `soundfile`.
