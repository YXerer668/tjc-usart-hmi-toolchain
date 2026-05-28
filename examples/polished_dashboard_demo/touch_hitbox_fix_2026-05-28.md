# Touch Hitbox Fix - 2026-05-28

## Scope

This note records the live `polished04_touchfix` dashboard build for the
`TJC8048X543_011C` panel on `COM36`.

## Root Cause

Direct `.pa` layout patching updated visible widget geometry fields (`x`, `y`,
`w`, `h`) but did not update hidden end-coordinate fields (`endx`, `endy`).
That allowed a button to render at its new position while its physical touch
hitbox remained at the old position.

The dashboard `logbtn` failure showed the pattern clearly:

- visible geometry: `x=416`, `y=386`, `w=104`, `h=52`
- stale hidden geometry in the broken build: `endx=639`, `endy=373`
- corrected hidden geometry: `endx=519`, `endy=437`

## Fix

The direct patch helpers now derive hidden hitbox ends whenever widget geometry
is patched:

```text
endx = x + w - 1
endy = y + h - 1
```

Updated helpers:

- `tools/codex_apply_hmi_patch_plan.py`
- `tools/codex_patch_hmi_layout_direct.py`

The physical touch probe was also tightened to classify touch zones and preserve
ASCII markers:

- `tools/codex_touch_coordinate_probe.py`

## Live Validation

Build output directory, kept out of normal git history:

```text
build/codex_fourpage_dashboard_polished04_touchfix/
```

Large generated artifacts were not committed. They are identified here by size
and SHA-256:

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `polished04_touchfix_compile.tft` | 11,485,348 | `C862934359E198C39EDDE904C14F0EB995780B243EDFDD93F62B49616CB87AD7` |
| `lcd_test.HMI` | 18,235,513 | `897B3498EF0ABEE7A639763EE5644B0DDC60553CB7E315B25884FF59927AD97A` |
| `camera_after_touchfix_upload.jpg` | 187,506 | `2F0D303853F062984DD42EDF43B84369693AA4F6370C2EA903B10393AC4788F6` |

Verification summary:

- official GUI compile: success, `0` errors, `0` warnings
- TFT checksum: valid, stored/calculated `0x445A528A`
- upload target gate: `mode=2`, `flash_descriptor=1089-0`,
  `model=TJC8048X543_011C`, `firmware=277`, `mcu_code=10501`,
  `feature_descriptor=128974848-0`
- post-upload health: `healthy=true`
- serial route: `click logbtn,0` followed by `sendme` returned page `3`
- manual physical check: user confirmed the repaired LOG path after flashing

## Follow-Up Rule

Any future `.pa` geometry patch workflow must treat `x/y/w/h` and `endx/endy`
as one geometry unit. Preview collision checks only prove visual layout; touch
hitbox checks must include the hidden end-coordinate fields.
