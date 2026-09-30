"""외부 음원을 사용하지 않고 명중·가드의 짧은 효과음을 생성한다.

48 kHz 모노 PCM 소스를 게임 에셋으로 가져온다. 고정 난수와 양 끝의
페이드로 같은 원본을 재현하고 파형 경계의 클릭을 방지한다.
"""
import argparse
import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 48000


def _render(duration, guarded):
    rng = random.Random(17 if guarded else 11)
    count = round(duration * SAMPLE_RATE)
    samples = []
    previous_noise = 0.0
    phase = 0.0
    for index in range(count):
        seconds = index / SAMPLE_RATE
        fade_in = min(1.0, seconds / 0.0015)
        fade_out = min(1.0, (count - 1 - index) / (SAMPLE_RATE * 0.015))
        noise = rng.uniform(-1.0, 1.0)
        high_noise = noise - previous_noise * 0.75
        previous_noise = noise
        if guarded:
            metal = sum(math.sin(2 * math.pi * frequency * seconds) * math.exp(-seconds * decay) * gain
                        for frequency, decay, gain in [(780, 18, 0.45), (1231, 25, 0.3), (2087, 35, 0.2)])
            value = metal + high_noise * math.exp(-seconds * 80) * 0.2
        else:
            frequency = 70 + 150 * math.exp(-seconds * 45)
            phase += 2 * math.pi * frequency / SAMPLE_RATE
            value = math.sin(phase) * math.exp(-seconds * 25) * 0.7 + high_noise * math.exp(-seconds * 70) * 0.45
        samples.append(value * fade_in * max(0.0, fade_out))
    peak = max(abs(sample) for sample in samples)
    gain = 0.68 / peak
    return [round(sample * gain * 32767) for sample in samples]


def generate(output_directory):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, duration, guarded in [("S_SC_Hit", 0.16, False), ("S_SC_Guard", 0.23, True)]:
        path = output_directory / (name + ".wav")
        samples = _render(duration, guarded)
        with wave.open(str(path), "wb") as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(SAMPLE_RATE)
            sound.writeframes(struct.pack("<" + "h" * len(samples), *samples))
        files[name] = path
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "sources")
    arguments = parser.parse_args()
    for sound_name, sound_path in generate(arguments.out).items():
        print(sound_name + ": " + str(sound_path.resolve()))
