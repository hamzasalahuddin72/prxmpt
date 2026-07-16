from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioDevice:
    id: str
    name: str
    kind: str
    is_default: bool = False

    @property
    def label(self) -> str:
        return f"{self.name}{' (Default)' if self.is_default else ''}"


def _soundcard():
    try:
        import soundcard as sc

        return sc
    except Exception as exc:
        raise RuntimeError(f"Audio support could not be loaded: {exc}") from exc


def _sounddevice():
    try:
        import sounddevice as sd

        return sd
    except Exception as exc:
        raise RuntimeError(f"Microphone support could not be loaded: {exc}") from exc


def _default_input_index(sd) -> int | None:
    try:
        value = sd.default.device
        try:
            value = value[0]
        except (IndexError, KeyError, TypeError):
            pass
        index = int(value)
        return index if index >= 0 else None
    except (IndexError, TypeError, ValueError):
        return None


def list_input_devices() -> list[AudioDevice]:
    """List PortAudio inputs.

    SoundCard's Windows backend assumes every driver exposes a particular
    floating-point WAVEFORMATEXTENSIBLE structure. A number of USB, headset,
    and virtual drivers do not, so v1.0.6 uses PortAudio for microphones while
    retaining SoundCard only for the working WASAPI loopback path.
    """
    sd = _sounddevice()
    default_index = _default_input_index(sd)
    devices = []
    for index, raw in enumerate(sd.query_devices()):
        if int(raw.get("max_input_channels", 0)) <= 0:
            continue
        devices.append(
            AudioDevice(
                str(index),
                str(raw.get("name") or f"Input {index}"),
                "microphone",
                index == default_index,
            )
        )
    return sorted(devices, key=lambda item: (not item.is_default, item.name.lower()))


def list_loopback_devices() -> list[AudioDevice]:
    sc = _soundcard()
    default_speaker = sc.default_speaker()
    default_id = getattr(default_speaker, "id", "") if default_speaker else ""
    loopbacks = [
        device
        for device in sc.all_microphones(include_loopback=True)
        if getattr(device, "isloopback", False)
    ]
    devices = [
        AudioDevice(str(device.id), str(device.name), "loopback", str(device.id) == default_id)
        for device in loopbacks
    ]
    return sorted(devices, key=lambda item: (not item.is_default, item.name.lower()))


def open_device(device_id: str, kind: str):
    sc = _soundcard()
    if kind == "loopback":
        if device_id:
            device = sc.get_microphone(device_id, include_loopback=True)
            if device is None:
                raise RuntimeError("The selected Windows output device is no longer available.")
            return device
        speaker = sc.default_speaker()
        if speaker is None:
            raise RuntimeError("No Windows output device was found.")
        device = sc.get_microphone(speaker.id, include_loopback=True)
        if device is None:
            raise RuntimeError("The default Windows output could not be opened for loopback.")
        return device
    if device_id:
        device = sc.get_microphone(device_id)
        if device is None:
            raise RuntimeError("The selected microphone is no longer available.")
        return device
    microphone = sc.default_microphone()
    if microphone is None:
        raise RuntimeError("No microphone was found.")
    return microphone


def input_device_index(device_id: str) -> int | None:
    """Resolve a stored PortAudio device index or the current Windows default."""
    sd = _sounddevice()
    if not device_id:
        index = _default_input_index(sd)
        if index is None:
            raise RuntimeError("No Windows default microphone was found.")
        return index
    try:
        index = int(device_id)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("The saved microphone selection is no longer valid.") from exc
    try:
        info = sd.query_devices(index)
    except Exception as exc:
        raise RuntimeError("The selected microphone is no longer available.") from exc
    if int(info.get("max_input_channels", 0)) <= 0:
        raise RuntimeError("The selected device does not provide microphone input.")
    return index


def open_input_stream(device_id: str, sample_rate: int):
    """Create a resilient float32 PortAudio stream for a Windows microphone."""
    sd = _sounddevice()
    index = input_device_index(device_id)
    info = sd.query_devices(index, "input")
    max_channels = max(1, int(info.get("max_input_channels", 1)))
    channel_candidates = tuple(dict.fromkeys((1, min(2, max_channels))))
    errors: list[str] = []
    for channels in channel_candidates:
        try:
            return sd.InputStream(
                device=index,
                samplerate=sample_rate,
                channels=channels,
                dtype="float32",
                blocksize=0,
            )
        except Exception as exc:
            errors.append(" ".join(str(exc).split()) or type(exc).__name__)
    raise RuntimeError(errors[-1] if errors else "The microphone stream could not be opened.")
