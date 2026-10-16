> **Source and scope:** User-provided setup notes, preserved below. Reported tests and timings describe the original host; they were not independently repeated for this repository. Commands and private APIs are version-specific and should be checked against the target Hermes version. These notes do not change any profile or enable STT automatically.

# Portable setup notes: faster-whisper medium

## What we actually configured and verified

- Engine: **faster-whisper**, not the original OpenAI Whisper CLI and not a cloud Whisper API.
- Installed faster-whisper version on the tested host: **1.2.1**. This is the observed version, not a claim that it is the latest available.
- Default model: **medium**, explicitly selected in default and every existing named Hermes profile.
- Provider setting: **local**. In the inspected Hermes version, this prefers faster-whisper when installed but can fall back to a local Whisper CLI when the dependency is missing. Therefore provider/model configuration alone is NOT enough to verify the engine.
- Language on the default profile: **en**. Other profiles' existing language/device/VAD settings were preserved; English was not forced across all profiles.
- Tested execution: CPU, **int8_float32**, selected automatically. No GPU was used for our benchmarks. Device/compute type were not explicitly pinned in our saved configuration.
- Final live verification: the gateway logged an actual incoming recording as `via local whisper (medium, lang=en, 34.6s audio)`. Native provider selection and the faster-whisper implementation were checked separately, so this was not inferred from a saved model name.

## 1. Hermes: install through its own package manager

On the target computer, first install/configure Hermes normally and identify the intended profile. Do not copy this computer's credentials, sessions, memory stores, virtual environment or absolute interpreter paths.

Run the native dependency setup hook:

```bash
hermes tools post-setup faster_whisper
```

For a named profile:

```bash
hermes -p PROFILE tools post-setup faster_whisper
```

This is the hook we actually used. Internally, the inspected Hermes version calls:

```python
pm.sync_venv(['stt-whisper'], explicit=True)
```

Prefer the native hook over pip-installing into whichever Python happens to be on PATH. Hermes may use a different managed dependency environment. The hook was accepted by our installed version even though its help text did not list the faster_whisper key; check the actual installed hook registry/docs if another version differs.

## 2. Select the provider and model explicitly

For default:

```bash
hermes config set stt.enabled true
hermes config set stt.provider local
hermes config set stt.local.model medium
hermes config set stt.language en
```

For another profile, insert `-p PROFILE` before `config` in each command. Apply separately to every existing profile that should use this default. Configuring default alone did NOT populate the named profiles' STT sections on our installation. Newly created future profiles also need their effective settings verified; this task did not change Hermes' profile-creation factory.

`stt.language en` is appropriate for these English recordings. Do not force it when you want other languages or automatic language detection; inspect the receiving agent's current language-selection rules.

The effective minimal configuration is:

```yaml
stt:
  enabled: true
  provider: local
  language: en
  local:
    model: medium
```

Use the config CLI to change Hermes settings; the YAML above documents the target, not a recommendation to overwrite the whole config file. Preserve unrelated settings and any existing device/compute/VAD policy.

Our config retained an old `stt.openai.model: whisper-1` section. That section did not select the backend: explicit `provider: local` and actual runtime resolution selected faster-whisper. Do not confuse an unused provider section with the active provider.

## 3. Download/cache the actual medium model

The first successful load downloads the CTranslate2-compatible model from **Systran/faster-whisper-medium** on Hugging Face. It needs network access and sufficient free disk/RAM. No speech API key was needed on our host. An unauthenticated-Hub rate-limit warning is not itself a transcription failure.

The model cache on our Linux host was under `~/.cache/huggingface/hub/`; cache locations can be overridden on other systems. Preserve partial/cache files when diagnosing downloads. A `.incomplete` weights file is not proof of a usable model.

Our first medium download stalled and timed out. A supported command-scoped retry with:

```bash
HF_HUB_DISABLE_XET=1 <the-agent-runtime-python> <your-model-load-or-transcription-script>
```

used the direct-HTTP download path and completed. This was a download workaround, NOT a required permanent STT setting. Do not start duplicate downloads while an earlier process is still running. Long downloads should use a tracked background process with completion notification and retained logs.

Do not copy the literal interpreter path from this machine: Hermes' dependency environment changed after installation. Discover the selected runtime on the target computer. In our installed source, `pm.environments.project_python(<Hermes-source-root>)` returned it; that is an implementation-specific diagnostic, not a universal public CLI.

## 4. Activate the dependency safely

Installing a dependency can select a new managed environment while an existing gateway keeps its old Python environment/import flags. A successful fresh-process test therefore does not prove a running Telegram gateway has adopted it.

If the installed Hermes version needs a gateway restart after dependency installation, coordinate it first. A shared gateway restart can interrupt other bots and active cron/agent work. Do not restart an entire fleet casually to test one profile.

Changing only small to medium did not require a separate dependency installation on our now-working faster-whisper runtime: the inspected loader reloads the cached model when the requested model name changes. Still verify the next real incoming voice note before declaring live adoption.

## 5. Verify the engine, not just the model setting

Read back:

```bash
hermes config get stt.provider
hermes config get stt.local.model
```

Expected values: `local` and `medium`.

Then send a short real voice message and inspect the receiving profile's logs. In our implementation:

```text
Loading faster-whisper model 'medium' ...
Transcribed ... via local whisper (medium, lang=en, ...s audio)
```

was the native faster-whisper path. By contrast:

```text
Transcribed ... via local STT command (small, ... chars)
```

was a command backend. Inspect that backend's executable/wrapper before identifying its engine: some command wrappers themselves use faster-whisper. On our old fallback, `~/.local/bin/whisper` imported `whisper.transcribe`, so it was the original OpenAI Whisper package, not faster-whisper.

In the inspected Hermes transcription module, the fresh-process checks were: faster-whisper import available in the selected runtime, `_get_provider(config) == 'local'`, successful native transcription, and `_local_model_name == 'medium'`. These private helper names may change between Hermes versions. The decisive user-facing check is an actual inbound transcription plus traced backend evidence.

One CLI version warned that `stt.provider` was an unrecognized config key even though the installed transcription consumer read it correctly. We verified the consumer and actual result rather than assuming either the warning or save success settled runtime behavior. Investigate such mismatches on the target version; do not ignore arbitrary warnings.

## 6. Decoding settings used in our benchmark

These were Hermes defaults/effective settings, not a collection of custom tweaks we had to add:

- `beam_size=5`
- `condition_on_previous_text=False`
- `vad_filter=True`
- VAD `min_silence_duration_ms=500`
- `no_speech_threshold=0.6`
- `log_prob_threshold=-1.0`
- language `en`
- no additional domain or phrase hints

We left device and compute type on auto; this host selected CPU/int8_float32. Do not claim CUDA is configured or required. If another machine needs explicit CPU/GPU settings, inspect its supported CTranslate2 compute types and runtime libraries first; changing the hardware path invalidates direct comparison with our CPU timings.

For a NON-Hermes Python agent, install faster-whisper in that agent's own supported environment and use `WhisperModel('medium')`, not `whisper.load_model`. A minimal integration mirroring our measured CPU/settings would be:

```python
from faster_whisper import WhisperModel

model = WhisperModel('medium', device='cpu', compute_type='int8_float32')
segments, info = model.transcribe(
    'recording.ogg',
    language='en',
    beam_size=5,
    condition_on_previous_text=False,
    vad_filter=True,
    vad_parameters={'min_silence_duration_ms': 500},
    no_speech_threshold=0.6,
    log_prob_threshold=-1.0,
)
text = ' '.join(segment.text.strip() for segment in segments)
print(text)
```

This standalone example is an integration sketch, not a separate program executed during our test. Our executed benchmark used the actual Hermes transcription API, including its additional confidence filtering. Consume `segments` before stopping a timer: decoding is lazy. Keep the model resident when practical instead of downloading/loading it on every utterance. Our `.ogg` recordings decoded successfully with faster-whisper's PyAV-backed path; Hermes may use additional conversion tooling for other input formats.

## 7. Measured speed and accuracy limitations

On the SAME 113.2-second user recording, with matched input hashes, Hermes source/config, CPU/int8_float32, one warmup and three timed repetitions:

- Tiny: median **2.00 seconds**, range 1.99–2.06.
- Small: median **9.55 seconds**, range 9.36–9.74.
- Medium: median **28.87 seconds**, range 28.43–29.82.
- Medium took **3.02 times** as long as small on this recording.

These exclude initial model loading/download, Telegram upload/queueing and assistant response. They are local observations, not promises for another computer. Host load and hardware affect speed.

Tiny badly changed technical terms: number walls → number worlds, patterns → fathers, application → obligation, Mandelbrot set → Mandal Broadset. Small preserved those terms; medium produced a cleaner ending but still mishandled the creator's name and a geometry/symmetries phrase. Larger is not error-free.

A separate corrected alphabet recording was transcribed accurately by medium in all three passes, ignoring punctuation/case. Small rendered foxtrot as box truth. That is a result for one known-reference clip, not general accuracy.

For a real accuracy benchmark, supply a human-verified verbatim reference and calculate WER from normalized words. Do not use an ASR transcript or a polished editorial reconstruction as the gold reference. Save all raw outputs and timing repetitions; do not cherry-pick the best transcription. Timing repeated deterministic outputs measures speed stability, not independent accuracy trials.

## Handoff checklist

- Correct agent/profile runtime has faster-whisper installed.
- Provider is local; model is medium; language policy is intentional.
- Model weights fully downloaded and load successfully.
- Existing gateway has adopted the dependency/configuration.
- A real incoming recording proves the actual engine/model used.
- Each named profile is checked separately; future profiles are not assumed configured.
- No copied credentials, virtualenvs, private memory or machine-specific paths.
- No uncoordinated shared-gateway restart, cloud speech fallback or schedule activation.
