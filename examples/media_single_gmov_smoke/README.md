# Single GMOV Smoke

这是当前动画控件最小、最窄的烧录样例。它只放一个内部
`animation` / `gmov` 对象，避免把 GMOV、video、audio 混在同一个 TFT
里导致资源调度问题。

## 两种构建方式

仓库里的 `scene.json` 默认只生成 GMOV 控件壳和文本说明，不内置 `.gmov`
资源。这样开源仓库不会携带官方/私有媒体资源，也能用于验证对象记录和
checksum：

```powershell
.\usarthmi.cmd --json scene build .\examples\media_single_gmov_smoke\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\media_single_gmov_smoke_build

.\usarthmi.cmd --json tft checksum `
  --file reverse_usarthmi\media_single_gmov_smoke_build\output.tft
```

如果要生成真实会动的内部 GMOV TFT，在本机复制一份 scene，并给 `gm0`
补上 fixture 资源：

```json
"resources": {
  "sources": [
    "C:\\Users\\SinYu\\Desktop\\case_for_codex\\case_47_gmov\\official_wiki\\extract\\0.gmov",
    "C:\\Users\\SinYu\\Desktop\\case_for_codex\\case_47_gmov\\official_wiki\\extract\\1.gmov",
    "C:\\Users\\SinYu\\Desktop\\case_for_codex\\case_47_gmov\\official_wiki\\extract\\2.gmov",
    "C:\\Users\\SinYu\\Desktop\\case_for_codex\\case_47_gmov\\official_wiki\\extract\\3.gmov"
  ]
}
```

构建成功时，`manifest.json` 里的 `tft_gmov_pack.resource_count` 应该是
`4`，`tft_checksum.valid` 应该是 `true`。如果 `tft_gmov_pack` 是 `null`，
说明这次只生成了 GMOV 控件壳，没有打包动画资源。

## 活屏验收

烧录后先做串口读回，再看摄像头。动画默认可以通过串口打开：

```powershell
python tools\live_tft_smoke.py `
  --file reverse_usarthmi\media_single_gmov_smoke_build\output.tft `
  --out-dir reverse_usarthmi\media_single_gmov_smoke_build\smoke_capture `
  --expect title.txt="SINGLE GMOV TFT" `
  --expect gm0.vid=0 `
  --expect gm0.loop=1 `
  --expect gm0.dis=100 `
  --set-expect gm0.en=1 `
  --capture
```

使用 `--upload --progress` 前，仍然遵守本项目的通用规则：先确认目标是
`COM36` 上的 `TJC8048X543_011C`，并且不要在官方串口下载过程中复制
`work\a-*\output\*.tft`。

## 当前边界

- 这个样例只承诺单个内部 GMOV。
- SD 卡路径 GMOV、video、audio 仍属于后续资源调度工作。
- 如果要研究混合媒体对象，请看 `examples/media_widgets_demo`，但它目前是
  HMI/preview authoring 样例，不是推荐烧录样例。
