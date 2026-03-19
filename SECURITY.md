# Security Policy

## Supported Packaging and Distribution Methods

Nocturne only supports [Flatpak](https://flatpak.org/) officially, any other packaging methods might not behave as expected.
Thus, official security-related support is only provided to the Flatpak distribution as of right now.
This may be subject to change in the future.

---

## Data Handling

### Library

- Any data related to the user's music library, history and playback is handled by the server and thus is out of the scope of Nocturne.
- If the user chooses to use the integrated Navidrome instance data handling will be managed by Navidrome.

### Lyrics

- Automatic lyric downloading is handled by [LRCLIB](https://lrclib.net/) via it's open API.
- Nocturne is not responsible for checking the ownership of the lyrics being downloaded
- Nocturne is not responsible for the data sent to LRCLIB in order to facilitate the lyrics
- Every time a lyric is requested it is downloaded locally as to not make multiple requests to LRCLIB
- [LRCLIB](https://github.com/tranxuanthang/lrclib) is an open source software project and thus can be subject to review by anyone

### Telemetry

- Nocturne does **not** include any telemetry.
- Servers like Navidrome or Subsonic might contain telemetry depending on the configuration.
- Nocturne requests for the integrated Navidrome instance telemetry to be off by default on installation.

### Password

- The password needed for connecting to a server is stored securely using the library `libsecret` which handles passwords in the device's keyring.

---

## What Nocturne Will **Never** Do

- Share library information outside of server - client interactions
- Collect usage data
- Facilitate content piracy

