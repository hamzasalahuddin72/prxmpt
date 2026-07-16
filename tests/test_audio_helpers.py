import threading

import numpy as np

import clearcue.audio.capture as capture_module
import clearcue.audio.devices as devices_module
from clearcue.audio.capture import AudioCapture, resample_linear, sample_rate_candidates
from clearcue.audio.devices import list_input_devices
from clearcue.audio.segmenter import SpeechSegmenter
from clearcue.audio.transcriber import TranscriptionWorker


def test_resample_length() -> None:
    source = np.linspace(-1, 1, 48_000, dtype=np.float32)
    output = resample_linear(source, 48_000, 16_000)
    assert len(output) == 16_000
    assert output.dtype == np.float32


def test_sample_rate_candidates_are_ordered_and_unique() -> None:
    assert sample_rate_candidates(44_100) == (44_100, 48_000, 16_000)


def test_capture_falls_back_from_stale_device_and_resamples(monkeypatch) -> None:
    audio_ready = threading.Event()
    captured = []
    states = []

    class InputStream:
        def __enter__(self):
            return self

        def __exit__(self, exception_type, exception, traceback) -> None:
            return None

        def read(self, numframes: int) -> tuple[np.ndarray, bool]:
            return np.full((numframes, 2), 0.05, dtype=np.float32), False

    def open_fake(device_id: str, sample_rate: int):
        if device_id == "stale-device":
            raise RuntimeError("device disappeared")
        return InputStream()

    monkeypatch.setattr(capture_module, "open_input_stream", open_fake)
    capture = AudioCapture(
        "stale-device",
        "microphone",
        48_000,
        lambda audio: (captured.append(audio), audio_ready.set()),
        on_state=lambda kind, available, message: states.append((available, message)),
    )
    capture.start()
    assert audio_ready.wait(1)
    capture.stop()
    assert captured
    assert len(captured[0]) == 320
    assert any(available for available, message in states)


def test_capture_logs_one_summary_per_retry_window(monkeypatch) -> None:
    warnings = []
    capture = AudioCapture(
        "",
        "microphone",
        48_000,
        lambda audio: None,
    )
    monkeypatch.setattr(capture_module.LOGGER, "warning", lambda *args: warnings.append(args))
    capture._log_retry_cycle(3, "driver rejected stream")
    capture._log_retry_cycle(3, "driver rejected stream")
    assert len(warnings) == 1


def test_portaudio_input_list_marks_windows_default(monkeypatch) -> None:
    class DefaultPair:
        def __getitem__(self, index: int) -> int:
            return (1, 4)[index]

    class FakeSoundDevice:
        class default:
            device = DefaultPair()

        @staticmethod
        def query_devices():
            return [
                {"name": "Output only", "max_input_channels": 0},
                {"name": "USB microphone", "max_input_channels": 2},
                {"name": "VoiceMeeter input", "max_input_channels": 8},
            ]

    monkeypatch.setattr(devices_module, "_sounddevice", lambda: FakeSoundDevice())
    devices = list_input_devices()
    assert [device.name for device in devices] == ["USB microphone", "VoiceMeeter input"]
    assert devices[0].is_default is True


def test_segmenter_emits_speech_with_energy_fallback() -> None:
    captured = []
    segmenter = SpeechSegmenter(captured.append)
    segmenter._vad = None
    speech = np.full(16_000, 0.08, dtype=np.float32)
    silence = np.zeros(16_000, dtype=np.float32)
    segmenter.feed(speech)
    segmenter.feed(silence)
    assert captured
    assert len(captured[0]) >= 16_000


def test_segmenter_emits_after_short_silence_for_low_latency() -> None:
    captured = []
    segmenter = SpeechSegmenter(captured.append)
    segmenter._vad = None
    segmenter.feed(np.full(4_800, 0.08, dtype=np.float32))
    segmenter.feed(np.zeros(6_400, dtype=np.float32))
    assert captured


class _FakeEngine:
    description = "fake engine"
    device = "cpu"
    model_name = "fake"

    def __init__(self) -> None:
        self.loaded = threading.Event()

    def load(self) -> None:
        self.loaded.set()

    def transcribe(self, audio: np.ndarray) -> str:
        return f"samples={len(audio)}"


def test_transcription_worker_preloads_and_emits() -> None:
    engine = _FakeEngine()
    ready = threading.Event()
    captured = []
    worker = TranscriptionWorker(
        "fake",
        "cpu",
        "int8",
        lambda speaker, text: (captured.append((speaker, text)), ready.set()),
        engine=engine,
    )
    worker.start()
    assert engine.loaded.wait(1)
    worker.submit("You", np.zeros(3_200, dtype=np.float32))
    assert ready.wait(1)
    worker.stop()
    assert captured == [("You", "samples=3200")]


def test_transcription_worker_recovers_when_cuda_fails_during_inference() -> None:
    ready = threading.Event()
    captured = []

    class CudaEngine(_FakeEngine):
        description = "fake cuda"
        device = "cuda"
        model_name = "tiny.en"

        def transcribe(self, audio: np.ndarray) -> str:
            raise RuntimeError("cublas64_12.dll is missing")

    class CpuEngine(_FakeEngine):
        description = "fake cpu"
        device = "cpu"
        model_name = "tiny.en"

    created = []

    def factory(model: str, device: str, compute_type: str):
        created.append((model, device, compute_type))
        return CpuEngine()

    worker = TranscriptionWorker(
        "tiny.en",
        "cuda",
        "float16",
        lambda speaker, text: (captured.append((speaker, text)), ready.set()),
        engine=CudaEngine(),
        engine_factory=factory,
    )
    worker.start()
    worker.submit("Interviewer", np.zeros(1_600, dtype=np.float32))
    assert ready.wait(1)
    worker.stop()
    assert created == [("tiny.en", "cpu", "int8")]
    assert captured == [("Interviewer", "samples=1600")]


def test_transcription_queue_drops_oldest_to_stay_live() -> None:
    worker = TranscriptionWorker(
        "fake",
        "cpu",
        "int8",
        lambda speaker, text: None,
        engine=_FakeEngine(),
        queue_size=2,
    )
    for size in (1, 2, 3):
        worker.submit("You", np.zeros(size, dtype=np.float32))
    assert worker.dropped_segments == 1
    queued = [worker._queue.get_nowait(), worker._queue.get_nowait()]
    assert [len(item[1]) for item in queued if item is not None] == [2, 3]
