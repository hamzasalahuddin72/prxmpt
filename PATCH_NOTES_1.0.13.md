# prxmpt 1.0.13

This patch repairs Gemini connectivity and makes provider failures actionable.

## Gemini connection repair

- Moves stateless answer streaming from the Interactions path to the broadly
  supported Gemini streaming GenerateContent endpoint.
- Uses Google's official `google-genai` client with a 45-second transport
  timeout and closes each completed or failed stream cleanly.
- Detects a configured Windows/environment proxy. When that proxy produces a
  connection failure before any answer text arrives, prxmpt safely retries once
  using a direct connection.
- Bundles SOCKS transport support in addition to ordinary HTTP proxy support.
- Never retries after a partial answer has streamed, preventing duplicated text.

## Clear failure messages

The Gemini connection test and live answer flow now distinguish:

- invalid or unauthorized API keys;
- free-tier/project quota limits;
- unavailable models;
- unsupported project regions;
- DNS resolution failure;
- proxy or VPN failure;
- TLS/certificate verification failure;
- firewall/network connection failure;
- timeout or temporary Gemini service unavailability.

No API key, prompt, transcript or answer text is added to diagnostic messages.

## Build

Run `BUILD_INSTALLER.bat` or `BUILD_UPDATE_V1.0.13.bat`. The finished update is
created as `installer\output\prxmptUpdate_1.0.13.exe`.
