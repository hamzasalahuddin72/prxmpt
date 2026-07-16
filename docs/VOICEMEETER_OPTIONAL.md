# Optional VoiceMeeter routing

ClearCue normally captures meeting audio directly through Windows WASAPI, so
VoiceMeeter is not required. Use it only if the meeting application and ClearCue
cannot share the same output device reliably, or if you need more control over
where audio is monitored.

VoiceMeeter is third-party donationware and is not included with ClearCue.
Download it only from <https://vb-audio.com/Voicemeeter/> and follow VB-Audio's
installation and licensing guidance. Its driver installation normally requires
administrator permission and a Windows restart.

## Basic route

1. Install VoiceMeeter and restart Windows.
2. Open VoiceMeeter.
3. Set **A1** to the physical headphones you will use.
4. In Teams, Zoom or the browser, choose **VoiceMeeter Input (VB-Audio
   VoiceMeeter VAIO)** as the speaker/output device.
5. Confirm in VoiceMeeter that the virtual-input meter moves and that **A** is
   enabled so you can hear the call through A1.
6. In ClearCue, open **Settings → Audio**, refresh devices and select the
   VoiceMeeter virtual input/output route that corresponds to the meeting audio
   under **Meeting/system audio**.
7. Select your real microphone separately under **Your microphone**.
8. Start a test call and confirm that ClearCue's Meeting audio meter moves.

The exact labels can vary between VoiceMeeter Standard, Banana and Potato. Use
the meters to verify the route instead of relying only on the device name.

## Avoiding duplicate audio

- Use headphones, not speakers.
- Do not send the microphone into the same loopback bus ClearCue is using unless
  you intentionally want a combined channel.
- Keep the microphone as ClearCue's separate input so transcripts can label
  “Interviewer” and “You”.
- Do not select two Windows playback routes for the meeting application.
- Stop ClearCue before changing the Windows or VoiceMeeter device graph, then
  refresh devices and restart the session.

## Removing VoiceMeeter

Stop ClearCue and communication applications first. Use VoiceMeeter's official
uninstaller, restart Windows, then restore the physical headphones as the
Windows and meeting-application output device. Refresh ClearCue's audio devices.

