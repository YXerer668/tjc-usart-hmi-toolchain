# Image Resource Demo

This is the focused live-smoke scene for a normal `image` widget backed by a
newly packed picture resource.

It uses the local `case_07_image_source_png_jpg` fixture image and expects the
generated runtime widget to report `photo1.pic=1`, `photo1.id=4`, and the fixed
geometry from `smoke.expect.json`.

The committed hardware evidence for the current `TJC8048X543_011C` panel is in
`hardware_verified_2026-05-17.json`. It records a full COM36 upload, serial
readback of `photo1.pic/id/x/y/w/h`, and a `USB Cam` capture artifact.

Live proof is intentionally narrower than arbitrary image support: it proves the
packed resource can be uploaded to the current `TJC8048X543_011C` and that the
image widget fields read back correctly. Camera capture is useful visual
evidence, but pixel-level image-content matching stays separate.
