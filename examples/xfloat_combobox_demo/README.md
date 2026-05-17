# XFloat + Combobox Demo

`scene.json` is the clean-rebuild fixture for `xfloat` and `combobox`.
`smoke.expect.json` is the COM36 smoke recipe for the serial-readable fields:
`xval.val/vvs1` and `cbval.val/down/txt`.

This does not prove all combobox interaction behavior. It only proves the
initial compiled runtime fields that can be checked through serial readback.
The first live attempt showed `xval.vvs0` reads back as `2` even though the
compiled primary fixture field is `0`, and `cbval.qty` is not runtime-readable
on this target, so those fields stay outside the smoke expect file.
