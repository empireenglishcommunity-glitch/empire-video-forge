#!/usr/bin/env python3
"""
Hybrid Editing Pipeline — Phase 1 / Task 1.3: word-level transcription.

Runs faster-whisper (large-v3) on the source audio and saves BOTH:
  - words.json : [{word, start, end}]  (drives karaoke captions + soft CC)
  - segments.json : [{start, end, text}] (line-level, for SRT)

Reused by the Shorts karaoke captions (Phase 3) and long-form soft CC (Phase 2)
so timing comes from ONE source of truth. GPU (cuda/float16) when available.

Fail-soft: writes empty lists if transcription fails; callers degrade gracefully.
"""
import json, os, sys


def transcribe(in_path, out_dir, model_size="large-v3", language="ar"):
    os.makedirs(out_dir, exist_ok=True)
    words_path = os.path.join(out_dir, "words.json")
    segs_path = os.path.join(out_dir, "segments.json")
    try:
        from faster_whisper import WhisperModel
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        model = WhisperModel(model_size, device=device, compute_type=compute)
        segments, info = model.transcribe(
            in_path, language=language, word_timestamps=True,
            vad_filter=True, beam_size=5)
        words, segs = [], []
        for seg in segments:
            segs.append({"start": round(seg.start, 3),
                         "end": round(seg.end, 3),
                         "text": seg.text.strip()})
            for w in (seg.words or []):
                words.append({"word": w.word.strip(),
                              "start": round(w.start, 3),
                              "end": round(w.end, 3)})
        json.dump(words, open(words_path, "w"), ensure_ascii=False)
        json.dump(segs, open(segs_path, "w"), ensure_ascii=False)
        return {"ok": True, "words": len(words), "segments": len(segs),
                "language": info.language, "device": device}
    except Exception as e:
        json.dump([], open(words_path, "w"))
        json.dump([], open(segs_path, "w"))
        return {"ok": False, "error": str(e)[:300]}


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else \
        "/kaggle/input/datasets/macalempire/eec-raw-video/english-pronunciation-tip.mp4.mp4"
    out = sys.argv[2] if len(sys.argv) > 2 else "/kaggle/working/words_out"
    res = transcribe(src, out)
    print(json.dumps(res, ensure_ascii=False))
    # show a small sample so we can eyeball word timing quality
    wp = os.path.join(out, "words.json")
    if os.path.exists(wp):
        w = json.load(open(wp))
        print("first 8 words:", json.dumps(w[:8], ensure_ascii=False))
