# External Local Dependencies

This repository keeps large downloaded utilities and nested third-party clones out of
the main Git history. The current local workspace uses:

- `external/TFTTool` from `https://github.com/UNUF/TFTTool.git`
- `external/nextion-font-editor` from `https://github.com/hagronnestad/nextion-font-editor.git`

The font helper currently expects the local `nextion-font-editor` checkout to build on
this Windows machine. The local checkout has one compatibility tweak:

- `NextionFontEditor/ZiLib/ZiLib.csproj`
- `TargetFrameworkVersion` changed from `v4.6.1` to `v4.8`

Generated binaries, downloaded official tools, screenshots, TFT/HMI outputs, and large
reverse-engineering fixtures should stay outside normal Git history unless they are
explicitly promoted to a small documented fixture.
