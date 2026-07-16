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


def list_input_devices() -> list[AudioDevice]:
    sc = _soundcard()
    default = sc.default_microphone()
    default_id = getattr(default, "id", "") if default else ""
    devices = [
        AudioDevice(str(device.id), str(device.name), "microphone", str(device.id) == default_id)
        for device in sc.all_microphones()
    ]
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
