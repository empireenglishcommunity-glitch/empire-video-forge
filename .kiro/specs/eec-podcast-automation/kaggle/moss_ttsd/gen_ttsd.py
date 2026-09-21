# ==========================================================================
# EEC "Yalla Fluent" — MOSS-TTSD generation helper (candidate English engine)
# --------------------------------------------------------------------------
# Verified working recipe for running MOSS-TTSD-v1.0 (8B, multi-speaker
# dialogue) on Kaggle's T4x2. See README.md in this directory for the full
# story of why device_map="auto" is broken for this model and how this
# module fixes it. Run on Kaggle (GPU T4x2, Internet ON).
#
# Usage (inside a Kaggle cell):
#   import urllib.request
#   urllib.request.urlretrieve("<RAW_URL>/kaggle/moss_ttsd/gen_ttsd.py", "gen_ttsd.py")
#   import gen_ttsd
#   model, processor = gen_ttsd.load_model()
#   gen_ttsd.generate_dialogue(model, processor,
#       speakers=[("ref1.wav", "[S1] reference transcript..."),
#                 ("ref2.wav", "[S2] reference transcript...")],
#       dialogue_text="[S1] line one [S2] line two ...",
#       out_path="/kaggle/working/out.wav")
# ==========================================================================
import os, sys, subprocess, time

MODEL_ID = "OpenMOSS-Team/MOSS-TTSD-v1.0"
REPO_DIR = "/kaggle/working/MOSS-TTS"


def install():
    """One-time setup: clone + pip install -e ., then REPAIR the numpy/numba
    versions the -e . step breaks (it pulls versions incompatible with
    Kaggle's pre-installed torch/transformers)."""
    def run(cmd):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-600:], r.stderr[-600:], flush=True)
        return r

    if not os.path.isdir(REPO_DIR):
        run(["git", "clone", "https://github.com/OpenMOSS/MOSS-TTS.git", REPO_DIR])
    os.chdir(REPO_DIR)
    run([sys.executable, "-m", "pip", "-q", "install", "--extra-index-url",
        "https://download.pytorch.org/whl/cu128", "-e", "."])
    # REPAIR: pin numpy/numba back to Kaggle-compatible versions (fixes
    # "cannot import name '_center' from numpy._core.umath'" on transformers import)
    run([sys.executable, "-m", "pip", "-q", "install", "numpy==2.0.2"])
    run([sys.executable, "-m", "pip", "-q", "install", "-U", "numba==0.60.0"])


def load_model(model_id=MODEL_ID, gpu0_budget="8GiB", gpu1_budget="13GiB"):
    """Load MOSS-TTSD with a device_map that WORKS on T4x2. device_map="auto"
    scatters emb_ext (extra audio embedding table) onto a different GPU than
    embed_tokens; get_input_embeddings() sums them directly with no device
    move -> RuntimeError. Fix: pin emb_ext to embed_tokens's device, and use
    an ASYMMETRIC max_memory budget (GPU0 hosts the embedding/head tables so
    it needs a smaller transformer-layer budget than GPU1)."""
    install()
    import torch
    from transformers import AutoModel, AutoProcessor, AutoConfig
    from accelerate import infer_auto_device_map, init_empty_weights

    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    processor.audio_tokenizer = processor.audio_tokenizer.to("cuda:0")
    processor.audio_tokenizer.eval()

    config = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
    with init_empty_weights():
        empty_model = AutoModel.from_config(config, trust_remote_code=True, dtype=torch.bfloat16)
    auto_map = infer_auto_device_map(
        empty_model, max_memory={0: gpu0_budget, 1: gpu1_budget},
        no_split_module_classes=getattr(empty_model, "_no_split_modules", None))
    embed_dev = auto_map.get("language_model.embed_tokens", 0)
    for k in list(auto_map):
        if "emb_ext" in k:
            auto_map[k] = embed_dev
    del empty_model

    model = AutoModel.from_pretrained(
        model_id, trust_remote_code=True, attn_implementation="sdpa",
        dtype=torch.bfloat16, device_map=auto_map)
    model.eval()
    return model, processor


def generate_dialogue(model, processor, speakers, dialogue_text, out_path,
                      max_new_tokens=1200, device="cuda:0"):
    """speakers: list of (ref_audio_path_or_url, ref_transcript_with_[Sn]_tag).
    dialogue_text: the [S1]/[S2]/... tagged text to generate (continuation mode).
    Writes a single WAV to out_path. Returns (out_path, elapsed_seconds)."""
    import torch, torchaudio, soundfile as sf

    target_sr = int(processor.model_config.sampling_rate)
    wavs, prompt_texts = [], []
    for ref_audio, ref_text in speakers:
        w, sr = torchaudio.load(ref_audio)
        if w.shape[0] > 1:
            w = w.mean(dim=0, keepdim=True)
        if sr != target_sr:
            w = torchaudio.functional.resample(w, sr, target_sr)
        wavs.append(w)
        prompt_texts.append(ref_text)

    reference_audio_codes = processor.encode_audios_from_wav(wavs, sampling_rate=target_sr)
    concat_prompt_wav = torch.cat(wavs, dim=-1)
    prompt_audio = processor.encode_audios_from_wav([concat_prompt_wav], sampling_rate=target_sr)[0]
    full_text = " ".join(prompt_texts) + " " + dialogue_text

    conversations = [[
        processor.build_user_message(text=full_text, reference=reference_audio_codes),
        processor.build_assistant_message(audio_codes_list=[prompt_audio]),
    ]]

    t0 = time.time()
    with torch.no_grad():
        batch = processor(conversations, mode="continuation")
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        outputs = model.generate(input_ids=input_ids, attention_mask=attention_mask,
                                 max_new_tokens=max_new_tokens)
        for message in processor.decode(outputs):
            audio = message.audio_codes_list[0]
            sf.write(out_path, audio.detach().cpu().to(torch.float32).numpy(), target_sr)
    return out_path, round(time.time() - t0, 1)
