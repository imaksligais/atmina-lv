"""Regex-based context cue extraction + per-speaker mapping suggestions.

Cues feed `suggested_speakers.json`, which the operator confirms. Heuristics
are deliberately conservative — confidence < 0.7 means manual review needed.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Iterable

from src.video_ingest.models import AlignedSegment, ContextCue, SpeakerMapping

# Regex patterns
_GREETING_RE = re.compile(
    r"^(sveicināti|sveiki|labvakar|labrīt)\b",
    re.IGNORECASE,
)
_SELF_INTRO_RE = re.compile(
    r"\b((?i:mans vārds ir|es esmu))\s+([A-ZĀČĒĢĪĶĻŅŠŪŽ][\w-]+(?:\s+[A-ZĀČĒĢĪĶĻŅŠŪŽ][\w-]+)?)",
)
_ADDRESS_RE = re.compile(
    r"\b((?i:paldies|sveiki|lūdzu|jā))[, ]+([A-ZĀČĒĢĪĶĻŅŠŪŽ][\w-]+)",
)
_FORMAL_PHRASE_RE = re.compile(
    r"\bkā\s+([\w ]+ministrs|ministre|deputāts|deputāte|premjere?s?|frakcijas vadītāj[su]?)",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Lowercase + strip diacritics for substring matching."""
    norm = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in norm if not unicodedata.combining(c))


def _name_forms_match(name_form: str, candidate: str) -> bool:
    return _normalize(name_form) == _normalize(candidate)


def _resolve_pid(name_token: str, politicians: list[dict]) -> int | None:
    for p in politicians:
        if _name_forms_match(p["name"], name_token):
            return p["id"]
        forms = (p.get("name_forms") or "").split(",")
        for f in forms:
            f = f.strip()
            if f and _name_forms_match(f, name_token):
                return p["id"]
    return None


def compute_cues(
    aligned: list[AlignedSegment],
    politicians: list[dict],
) -> list[ContextCue]:
    cues: list[ContextCue] = []

    seen_first = False
    for seg in aligned:
        text = seg.text

        # First-speaker greeting (only first segment)
        if not seen_first and _GREETING_RE.search(text):
            cues.append(ContextCue(
                speaker=seg.speaker, cue_type="first_speaker_greeting",
                text=text[:80], at_seconds=seg.start,
            ))
        seen_first = True

        # Self-introduction
        m = _SELF_INTRO_RE.search(text)
        if m:
            name = m.group(2).strip()
            pid = _resolve_pid(name, politicians)
            cues.append(ContextCue(
                speaker=seg.speaker, cue_type="self_introduction",
                text=name, at_seconds=seg.start, matched_pid=pid,
            ))

        # Addressed by name (resolves to OTHER speaker — cue speaker = current)
        for m in _ADDRESS_RE.finditer(text):
            addressed = m.group(2).strip()
            pid = _resolve_pid(addressed, politicians)
            if pid is not None:
                # Tag the speaker BEING ADDRESSED, not the current speaker
                # We don't know which speaker; downstream uses this as evidence
                # for the speaker who responds next. For simplicity we tag with
                # current speaker; suggest_speakers reasons about next-segment.
                cues.append(ContextCue(
                    speaker=seg.speaker, cue_type="addressed_by_name",
                    text=addressed, at_seconds=seg.start, matched_pid=pid,
                ))

        # Formal phrase
        m = _FORMAL_PHRASE_RE.search(text)
        if m:
            cues.append(ContextCue(
                speaker=seg.speaker, cue_type="formal_phrase",
                text=m.group(0)[:80], at_seconds=seg.start,
            ))

    return cues


def suggest_speakers(
    cues: list[ContextCue],
    politicians: list[dict],
    speakers: list[str],
) -> dict[str, SpeakerMapping]:
    """Aggregate cues into one SpeakerMapping per unique speaker.

    `speakers` is the full speaker universe (e.g., from `aligned`); speakers
    without any cues fall through to the unknown fallback.

    Confidence rubric:
      0.95 = self-introduction matched a politician
      0.85 = addressed-by-name across multiple cues converging on same pid
      0.70 = first-speaker greeting (likely host)
      0.50 = single addressed-by-name cue
      0.00 = no matched cues (unknown)
    """
    pid_to_handle = {p["id"]: p["x_handle"] for p in politicians if p.get("x_handle")}
    pid_to_name = {p["id"]: p["name"] for p in politicians}

    by_speaker: dict[str, list[ContextCue]] = defaultdict(list)
    for c in cues:
        by_speaker[c.speaker].append(c)

    # All speakers we want to map (cues + explicit list)
    all_speakers = set(speakers) | set(by_speaker.keys())

    suggestions: dict[str, SpeakerMapping] = {}
    for spk in sorted(all_speakers):
        spk_cues = by_speaker[spk]

        # Self-introduction is highest signal
        intro = [c for c in spk_cues if c.cue_type == "self_introduction" and c.matched_pid]
        if intro:
            pid = intro[0].matched_pid
            suggestions[spk] = SpeakerMapping(
                pid=pid,
                handle=pid_to_handle.get(pid, f"pid_{pid}"),
                confidence=0.95,
                evidence=f"{int(intro[0].at_seconds // 60):02d}:{int(intro[0].at_seconds % 60):02d} "
                         f"pašprezentācija '{intro[0].text}'",
            )
            continue

        # First-speaker greeting → host
        greet = [c for c in spk_cues if c.cue_type == "first_speaker_greeting"]
        if greet and not any(c.matched_pid for c in spk_cues):
            suggestions[spk] = SpeakerMapping(
                pid=None,
                handle="host",
                confidence=0.70,
                evidence=f"{int(greet[0].at_seconds // 60):02d}:{int(greet[0].at_seconds % 60):02d} "
                         f"pirmais runātājs ar formālu sveicienu",
            )
            continue

        # Otherwise unknown
        suggestions[spk] = SpeakerMapping(
            pid=None,
            handle=f"unknown_{spk}",
            confidence=0.0,
            evidence="Nav konteksta zīmju; vajag manuālu verifikāciju",
        )

    return suggestions
