# Contributing

Thanks for helping improve `usarthmi`. This project is reverse-engineering
heavy, so the most useful contributions are small, reproducible, and backed by
evidence.

## Ground Rules

- Do not commit official editor binaries, proprietary `.HMI` / `.TFT` / `.zi`
  payloads, local screenshots, large captures, or generated build folders.
- Prefer small fixtures and text analysis over binary blobs. If a binary sample
  is required, describe where it came from and why it is legally shareable.
- Keep generated uploads conservative. The supported public path is full serial
  upload; sparse/smart download behavior is research-only.
- When adding a recovered widget or file-format feature, include at least one
  proof point: byte comparison, parser regression test, checksum validation,
  serial readback, or live-panel photo/capture.

## Development

Install in editable mode:

```powershell
python -m pip install -e .
```

Run focused tests while iterating:

```powershell
python -m pytest tests/test_protocol.py tests/test_scene_layout.py -q
```

Run the broader suite before publishing when your local fixture set is present:

```powershell
python -m pytest -q
```

Some tests intentionally skip when private/local reverse-engineering fixtures
are missing.

## Reporting Results

Please include:

- screen model and firmware when known;
- command used to build or upload;
- checksum output for generated `.TFT` files;
- serial readback such as `sendme` or `get obj.attr`;
- whether the result was verified by preview only, official GUI compile,
  or a real panel.
