import os
import subprocess
import sys
import tempfile
from pathlib import Path


def synthesize_speech(text: str, out_wav: Path) -> bool:
    """Synthesize speech using native OS TTS:

    - macOS: 'say'
    - Windows: SAPI SpeechSynthesizer via PowerShell
    Returns True if successful and file exists with > 1000 bytes.
    """
    out_wav = Path(out_wav).resolve()
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    # Method 1: macOS 'say'
    if sys.platform == "darwin":
        aiff = out_wav.with_suffix(".aiff")
        res = subprocess.run(["say", "-o", str(aiff), text], capture_output=True, text=True)
        if res.returncode == 0 and aiff.exists():
            # Convert to 48kHz mono WAV
            subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", str(aiff), "-ar", "48000", "-ac", "1", str(out_wav)], capture_output=True)
            aiff.unlink(missing_ok=True)
            if out_wav.exists() and out_wav.stat().st_size > 1000:
                return True

    # Method 2: Windows System.Speech.Synthesis
    if sys.platform == "win32":
        ps_script = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile('{str(out_wav).replace("'", "''")}')
$synth.Speak('{text.replace("'", "''")}')
$synth.Dispose()
"""
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as f:
            f.write(ps_script)
            tmp_ps1 = f.name
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp_ps1],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if res.returncode == 0 and out_wav.exists() and out_wav.stat().st_size > 1000:
                # Ensure 48kHz mono
                tmp_conv = out_wav.with_suffix(".conv.wav")
                subprocess.run(
                    ["ffmpeg", "-y", "-v", "quiet", "-i", str(out_wav), "-ar", "48000", "-ac", "1", str(tmp_conv)],
                    capture_output=True,
                )
                if tmp_conv.exists() and tmp_conv.stat().st_size > 1000:
                    tmp_conv.replace(out_wav)
                return True
        finally:
            Path(tmp_ps1).unlink(missing_ok=True)

    return False


if __name__ == "__main__":
    test_out = Path("test_sapi.wav")
    ok = synthesize_speech("Knights fought across medieval battlefields with heavy steel armor.", test_out)
    print(f"synthesize_speech: ok={ok}, size={test_out.stat().st_size if test_out.exists() else 0}")

