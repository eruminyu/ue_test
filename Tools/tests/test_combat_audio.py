"""게임 효과음 소스의 파일 형식·길이·클리핑·재현성을 검사한다."""
import importlib.util
import struct
import tempfile
import unittest
import wave
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "audio" / "generate_combat_audio.py"


class CombatAudioTest(unittest.TestCase):
    def test_export_is_reproducible_and_has_silent_boundaries(self):
        specification = importlib.util.spec_from_file_location("combat_audio", SCRIPT)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            first = module.generate(Path(directory) / "first")
            second = module.generate(Path(directory) / "second")
            self.assertEqual(set(first), {"S_SC_Hit", "S_SC_Guard"})
            for name, path in first.items():
                self.assertEqual(path.read_bytes(), second[name].read_bytes())
                with wave.open(str(path), "rb") as sound:
                    self.assertEqual((sound.getnchannels(), sound.getsampwidth(), sound.getframerate()), (1, 2, 48000))
                    duration = sound.getnframes() / sound.getframerate()
                    self.assertGreater(duration, 0.08)
                    self.assertLess(duration, 0.4)
                    raw = sound.readframes(sound.getnframes())
                samples = struct.unpack("<" + "h" * (len(raw) // 2), raw)
                self.assertEqual((samples[0], samples[-1]), (0, 0))
                self.assertGreater(max(abs(value) for value in samples), 8000)
                self.assertLess(max(abs(value) for value in samples), 30000)


if __name__ == "__main__":
    unittest.main()
