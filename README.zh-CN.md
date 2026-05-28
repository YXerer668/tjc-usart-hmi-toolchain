# usarthmi 中文说明

`usarthmi` 是一个面向陶晶驰 / USART HMI 串口屏的开源、证据驱动工具链。它把 Python CLI、`.HMI` / `.TFT` 解析、scene authoring、预览和重叠检查、串口上传验证，以及官方 `USART HMI` 编辑器的无鼠标 headless 编译桥接放到一条可复用流程里。

这个项目最开始来自一块 `TJC8048X543_011C`、`800x480` 串口屏的实机逆向。目标不是“立刻完整替代官方 USART HMI 编辑器”，而是把常用流程逐步变成可脚本化、可测试、可复现的命令行工具：

1. 用 JSON/YAML 描述页面。
2. 在电脑端生成预览图。
3. 生成可检查的 `.HMI`。
4. 对已经恢复格式的控件，独立生成可烧录的 `.TFT`。
5. 通过串口上传到屏幕，并用 `sendme` / `get obj.attr` 做实机验证。

项目许可证是 MIT。代码和逆向说明可以公开使用；官方编辑器二进制、官方资源包、个人生成的 `.HMI` / `.TFT` / `.zi` 大文件不进入仓库。

## 你可以用它做什么

- 检查 `.HMI` / `.TFT` 文件并渲染页面预览。
- 用 JSON/YAML 编写页面，编辑控件和事件，生成给 agent 交接的 preview/context 包。
- 通过官方编译器做无鼠标、headless 的 touch-safe 构建。
- 在烧录前检查可见重叠和隐藏触摸热区 `endx` / `endy` 不一致。
- 通过公开串口协议上传 TFT，并用 `sendme` / `get` / camera 证明实机状态。
- 打包成 Windows 发布包，让另一台装了官方 `USART HMI` 的机器复用。

## 快速开始

```powershell
python -m pip install -e .
python -m usarthmi --json scene check examples\polished_dashboard_demo\scene.json --out-dir build\scene_check
python tools\package_touchsafe_headless_toolchain.py --out-dir dist --require-host-exe
```

走 touch-safe 官方无头编译链路：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\touchsafe_headless_bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\tools\run_touchsafe_pipeline.ps1 `
  -Spec .\examples\polished_dashboard_demo\touchsafe_pipeline.template.json
```

默认只构建不烧录。烧真实屏幕必须显式加 `-Flash`，并确认 spec 里的目标型号门禁匹配当前屏。

## Agent Skills

仓库里的 [`skills/`](skills/) 目录提供给 Codex/agent 使用的流程说明：

- `usarthmi-headless-toolchain`：打包、bootstrap、官方 GUI 无头编译。
- `usarthmi-scene-authoring`：离线 scene 编辑、预览、lint、agent handoff。
- `usarthmi-live-panel-validation`：checksum、串口上传、健康探针、相机证据。

## 当前定位

这是一个“证据驱动”的逆向工具链。一个功能如果被标成可用，至少应该有一种证据支撑：

- 官方 fixture 的字节对齐。
- TFT checksum 通过。
- 串口 `get` / `sendme` 读回正常。
- 摄像头或人工确认实机显示正常。
- 对应单元测试或回归测试。

所以文档里会很直接地区分：稳定可用、实验可用、只支持 authoring/预览、仅研究记录、尚未实现。

完整状态表见 [FEATURE_STATUS.md](FEATURE_STATUS.md)。

## 已经比较能用的部分

- 串口运行时命令：`connect`、`sendme`、`get`、`set`、`page`、`ref`、`vis`、`tsw`、`click`、`dim`。
- `.HMI` 检查和拆包：能读出容器项、`Program.s`、`0.pa`、页面对象和部分事件脚本。
- 场景文件：支持 JSON/YAML，能做布局求解和规范化输出。
- 预览器：能渲染 scene、`.HMI`、`.pa`，并且可以使用真实 `.zi` 字库显示中英文。
- HmiSafe mode 3 TFT finalizer：能把已抓取的 pre-HmiSafe 中间 TFT 封装成和官方 final TFT 逐字节一致的输出，并有真实 pre/final fixture 做回归。
- 当前 `800x480` 种子工程的 page0 TFT 生成：支持追加/重建一批已经恢复的控件。
- 图片资源：支持 PNG/JPG 导入、TFT 图片资源打包、透明 PNG 展平、图片按钮两态资源。
- 字库：支持生成/替换 `.zi`；`tft build --font-zi` 可以在一次构建里同时替换
  `output.hmi` 和 `output.tft` 的安全字体槽，完整 GB2312 中文/英文小字库路线已经实机验证。
- 外部图片控件：推荐用健康的 `case_00_baseline` 资源布局，SD 卡路径如 `sd0/1.jpg` 已经实机验证。
- 动画控件：单个内部 GMOV 的 smoke 路线已经跑通；混合媒体还在研究。
- 多页实验：支持新增 page1 的普通控件/按钮事件，也支持用 `patch_seed_page0_widgets` 给 seed page0 里已有按钮补窄范围事件，便于做双页双向跳转探针。

## 已恢复或部分恢复的控件

当前工具链里已经有 fixture 或实机证据的控件包括：

- 文本、按钮、数字、图片、图片按钮。
- 进度条、滑块、仪表、二维码。
- 定时器、变量、双态按钮、状态按钮。
- 复选框、单选框、热点触摸区、触摸捕捉。
- 虚拟浮点数 `xfloat`、下拉框 `combobox`。
- 裁剪图、波形、滚动文本。
- 外部图片、单 GMOV 动画。

这些控件并不都等价于“全生态稳定支持”。很多控件目前是“当前 seed + 当前屏幕 + 当前 fixture”条件下可构建，换型号或换资源布局需要重新验证。
当前目标 supported 控件的离线完工边界见 `examples/all_supported_controls_completion_audit_2026-05-17.json`；它只证明 writer path 和 clean full-page rebuild 覆盖，不等于每个控件都有 COM36 活屏行为闭环。

## 还没完全解决的部分

- 完整官方编辑器替代：还不能无损反编译/重建所有官方 `.HMI` 工程。
- 跨型号通用 TFT 编译器：目前不作为主线目标；主线先服务 `TJC8048X543_011C`、`800x480`、当前种子工程。
- 页面重建：`examples/number_demo/full_page_rebuild_scene.json` 是最小 P1.6 实机闭环。它用 `drop_seed_objects` 删除 seed 对象 `t0/b0/p0`，重建 `page0/title/incbtn/numval`，并在完整 COM36 串口烧录后证明 `incbtn -> numval.val++` 事件仍然可用。最终视觉通过版本使用完整 GB2312 `UiCNEN32GBFull.zi` 和 `numval.lenth=3`；早先 UTF-8 稀疏字库版本串口可过但屏幕会显示错误字形。`examples/number_demo/reorder_broadening_scene.json` 只做离线结构拓宽，覆盖 `page0/status/incbtn/title/footer/numval` 的 text/button/number 重排；`examples/number_demo/event_matrix_scene.json` 只做离线事件保持矩阵，覆盖 clean rebuild 后的 `ref`、`vis`、`tsw` 和数值 `++` 字节码。这个结论还不能外推成“任意页面/任意控件都支持 full-page rebuild”。
- 事件调度：能编译/反解一小部分事件字节码；`ref obj` 已经通过 page0 场景 DSL、TFT 烧录、串口点击和摄像头遮盖重绘做过实机闭环。`examples/number_demo` 的 page0 `incbtn` 按下事件也已实机闭环：两次串口 `click incbtn,1` 把 `numval.val` 从 `123` 验到 `125`，并通过 `printh` 发出 `23 02 4e 31`。`examples/number_demo/tsw_promotion_scene.json` 也已烧录到 COM36，证据在 `examples/number_demo/tsw_promotion_serial_click_hardware_verified_2026-05-16.json`：它证明 clean rebuild 页面和 `disablebtn/enablebtn` 的 T0/T1 事件到达，但 `tsw targetbtn,0` 后串口 `click targetbtn,1` 仍会发出 TG；同一串口会话的 0/10/20/50/100/200 ms 快速时序扫描做了 18 次 critical 试验，全部先看到 T0 再看到 TG，所以这不是指令发太慢导致的串口 click 漏判。这仍只是 serial-click-path 的负结果，不是 physical touch-lockout 证明。page0 定时器 `codestimer-` 已经实机验证过运行时 `tm0.en=1` 后执行 `numval.val++`。page1 普通按钮事件已经实机验证过 `page 1` 跳页、显式十六进制 `printh`、同页一层 `click` 级联、数值字段 `++` / `=` / `--`，以及同页 `vis obj,0/1` 显示/隐藏操作。媒体事件 `wav0.vid=0`、`wav0.en=1`、`play 0,0,0` 已经有官方 fixture 字节对齐证据，但开机自动调度、实机 page-load / 通用调度还没完全闭环。
- 视频和音频资源调度：HMI/预览/记录结构已有，但独立 TFT 的资源 scheduler 还没彻底恢复。
- 官方“相同块跳过下载”：已经做过抓包和分析，但它在测试机上会把 Windows USB/PnP 搞成幽灵 COM，主线不再推荐。
- 官方 GUI oracle 现在要求编译前二次确认：脚本点击、patch 或手工编辑结束后，必须重新用官方编辑器打开最终 HMI，截图保存
  `before_official_compile_confirmation.png`，关闭并经官方保存后再解析对象/事件，写出
  `precompile_confirmation.json`。这个 manifest 没有证明预期对象名、type code 和必要事件行都存在时，不能继续编译并把输出当正向 oracle；高风险/负向官方探针也必须带这个 manifest，否则不能把后续 compile collapse 或 live 失败当作控件边界证据。
- 高级控件：`case_38/41/42/43/44` 已用官方 GUI 真实点击工具箱创建并保存，随后官方编译和 `work\a-*\output\*.tft` 提取均完成。`text-select`(`D`)、`sliding-text`(`>`)、`data-record`(`B`)、`file-browser`(`A`) 和 `file-stream`(`?`) 现在都属于当前目标已支持控件，走的是 fixture-backed current-target writer 路径：本地 scene build / donor 编辑生成的单控件或已审计变体 TFT 与官方 GUI 输出逐字节一致或与其对应 donor/oracle 路径一致，并已在 `COM36` 实机上传读回。case42/43/44 仍保留更窄的 claim 边界，不声称任意属性合成、未文档化的同页混合原生综合、文件/数据副作用或未验证事件行为。详见 [CURRENT_TARGET_LIMITATIONS.md](CURRENT_TARGET_LIMITATIONS.md) 和 `examples/advanced_widget_case_outputs_2026-05-17.json`。
- 官方 GUI 自动化（实验）：现在有一个声明式 spec runner，能把反编译 `appobjsclass.cs` 里的控件元数据、`HMIFORM\main.cs` 里的 toolbox 顺序、当前 GUI 校准值和现有的官方 GUI helper 串起来，自动执行 `select-page`、`create-widget`、`patch-field`、`patch-rect`、`patch-event`、`save-and-close`、`precompile-confirm`、`compile-capture`。入口是 `tools\official_hmi_automation.py`。`create-widget` 现在优先走 decompiled toolbox `message-index` 路径：按 `RefGongjuItem()` 里的真实控件顺序发 `WM_KEYDOWN/WM_LBUTTONUP`，不再只靠 page1/page0 的屏幕 Y 坐标赌命中。先看 registry：

```powershell
python tools\official_hmi_automation.py --dump-decompiled-registry
```

先 dry-run 看 spec 会展开成什么动作：

```powershell
python tools\official_hmi_automation.py `
  --spec-json examples\official_gui_automation_specs\case73_page1_textselect_minimal.json `
  --dry-run
```

如果 GUI 坐标带漂移，runner 也可以吃现有 toolbox scan 结果来覆盖默认校准。先扫：

```powershell
python tools\official_gui_toolbox_scan.py `
  --out-dir reverse_usarthmi\toolbox_scan_page1_textselect `
  --page-index 1 `
  --y-values 320 334 348 `
  --wheel-values 0
```

然后把得到的 `scan_report.json` 路径写进 automation spec 的
`page0_scan_report` 或 `page1_scan_report`；runner 会按 `first_added_type`
把 `tool_rel_y/toolbox_wheel` 覆盖到对应控件的当前校准值上。

仓库里现在附了多条示例 spec：

- `examples\official_gui_automation_specs\case73_page1_textselect_minimal.json`
- `examples\official_gui_automation_specs\case60_filebrowser_textselect_button_event.json`
- `examples\official_gui_automation_specs\case60_filebrowser_textselect_button_event_gui_patch.json`
- `examples\official_gui_automation_specs\page0_datarecord_slidingtext_minimal.json`
- `examples\official_gui_automation_specs\page0_button_gui_patch_minimal.json`
- `examples\official_gui_automation_specs\page0_button_gui_event_patch_minimal.json`

当前 worktree 已经有几条真实 non-dry-run 闭环证据：

- `case73_page1_textselect_minimal.json`：page1 `text-select` GUI 建控、`precompile-confirm` 和 `compile-capture` 全部通过。
- `case60_filebrowser_textselect_button_event.json`：page0 `file-browser + text-select + button` GUI 建控、离线 `patch-field/patch-rect/patch-event`、`precompile-confirm` 和 `compile-capture` 全部通过。
- `case60_filebrowser_textselect_button_event_gui_patch.json`：page0 `file-browser + text-select + button` GUI 建控后，继续通过官方属性表和官方事件编辑器修改 `eventbtn`，并通过 `precompile-confirm` 和 `compile-capture`。
- `page0_datarecord_slidingtext_minimal.json`：page0 `data-record + sliding-text` GUI 建控、`precompile-confirm` 和 `compile-capture` 全部通过。
- `page0_button_gui_patch_minimal.json`：page0 普通 `button` GUI 建控后，继续通过官方属性表 `dataGridView1` 自动修改 `objname/txt/x/y/w/h`，再通过 `precompile-confirm` 和 `compile-capture`。
- `page0_button_gui_event_patch_minimal.json`：page0 普通 `button` GUI 建控后，继续通过官方事件编辑器写入 `codesdown-1 / printh ...`，并由 `precompile-confirm` 显式验证事件 token 已保存。

它们还不是“完全官方等价替代”，但已经把 page/page1 选择、GUI 建控、离线 HMI patch、GUI 属性表编辑、GUI 事件编辑、编译前确认和官方 compile capture 串成一条统一入口，后续可以在这条 runner 上继续扩更多属性、更多控件和更多 oracle case。

## HmiSafe TFT finalizer

`usarthmi.tft_hmisafe` 现在提供已验证的 mode 3 finalizer 库函数和 CLI。它只复现官方 `HmiSafeWriteTFTFileSafe` / `ACServerGetFileCRC` 的最终封装边界：改写 400-byte TFT header 的已知字节和 header CRC，应用 mode 3 的 Appfree10 header XOR，并写入 EOF-4 小端校验值。它不构建资源段、不压缩 payload、不绕过授权、不 patch 官方程序，也不替代前面的完整编译流程。

```powershell
python -m usarthmi --json tft hmisafe-finalize `
  --input path\to\pre_hmisafe.tft `
  --out path\to\reproduced.tft `
  --final path\to\official_final.tft

python -m usarthmi --json tft hmisafe-verify --file path\to\official_final.tft
```

回归 gate 来自 `examples/control_fixture_library_2026-05-21.json`：真实 x32dbg 抓到的 `pre_hmisafe.tft` 必须生成和官方 final TFT byte-identical 的 `reproduced.tft`。`mode == 0x64` / `Appfree11Encode` 目前只从 native 代码中识别出来，还没有真实 pre/final 样本验证；所有 finalize/write 路径都会 fail-closed，直到补到对应样本。

## 安装

```powershell
python -m pip install -e .
```

依赖写在 `pyproject.toml`，主要是：

- `pyserial`
- `Pillow`
- `PyYAML`

## Python 接口和控件能力表

仓库现在把可用能力收敛在两个稳定入口：

- `usarthmi.api`：给外部脚本调用，包含 `validate_scene_file`、
  `validate_scene_document`、`build_scene_artifacts`、
  `import_hmi_file`、`inspect_hmi_file`、`inspect_tft_file`、`list_tft_models`、
  `list_widget_capabilities`、`get_widget_capability`、
  `get_capability_manifest`、`get_current_target_completion_audit`、
  `get_current_target_status_summary`、`get_builder_calibration_status`、
  `get_page1_filebrowser_frontier_report`、`get_next_live_probe_bundle` 和
  `get_page1_filebrowser_native_init_compare_targets_report`、
  `run_next_live_probe`。
- `usarthmi.widgets`：集中维护控件注册表，包括控件别名、支持状态、
  writer 类型、fixture case、TFT type code、pending/unsupported 原因。

以后补新控件时，优先在 `usarthmi.widgets` 增加或更新注册项，再让
`scene`、`editor` 和测试从同一份元数据拿结论，避免 README、矩阵、
scene 校验和 TFT writer 各自漂移。

CLI 也能直接读这份注册表：

```powershell
python -m usarthmi --json capabilities --widget filebrowser
python -m usarthmi --json editor capabilities
python -m usarthmi --json target summary
python -m usarthmi --json target audit
python -m usarthmi --json target calibration
python -m usarthmi --json target frontier
python -m usarthmi --json target compare-targets
python -m usarthmi --json target next-probe
python -m usarthmi --json target check-next-probe
python -m usarthmi --json target run-next-probe --result-json reverse_usarthmi\next_probe\run_next_probe_result.json
python -m usarthmi --json widgets list --support supported
python -m usarthmi --json widgets show filebrowser
python -m usarthmi --json widgets manifest --include-aliases
python -m usarthmi --json widgets template qrcode --id qr0 --x 80 --y 96
```

给人和 agent 交接页面时，优先生成只读预览包：

```powershell
python -m usarthmi --json scene check examples\polished_dashboard_demo\scene.json `
  --out-dir reverse_usarthmi\scene_check `
  --simulate-events `
  --scenario <scenario.yaml>

python -m usarthmi --json scene agent-preview examples\polished_dashboard_demo\scene.json `
  --out-dir reverse_usarthmi\gui_agent_preview
```

`scene check` 是离线版 Compile diagnostics：它会校验 scene、统计控件能力和
direct TFT 阻塞项、运行事件 lint/跳页图，并可用 `--simulate-events` 对所有非空
事件槽做有步数上限的离线模拟；也可以用可重复的 `--scenario` 跑显式
trigger/assert 场景文件。提供 `--out-dir` 时会写 `scene_check_report.json`。
它不生成 TFT、不打开串口、不烧录，报告里保持 `safe_to_flash=false`。

这个命令会输出 `preview.png`、`preview.annotated.png`、
`scene.normalized.json`、`agent_context.json`、`diagnostics.json`、
`capability_report.json`、`event_snippets.json` 和 `build_manifest.json`。其中
`agent_context.json` 包含控件坐标、能力状态、事件摘要、跳页图、诊断信息、
安全命令和默认禁止上传的 hardware policy；预览包不构建 TFT、不打开串口、
不烧录屏幕。

已有官方 `.HMI` 也可以先导入成一个有损但可编辑的 scene 包，方便 agent 接手：

```powershell
python -m usarthmi --json hmi import path\to\project.HMI `
  --out-dir reverse_usarthmi\imported_project `
  --overwrite
```

它会输出 `scene.imported.json`、`import_report.json`、预览图片和
`agent_context.json`。导入器会保留已经恢复出来的页面/对象坐标、文本、数值、
样式、资源字段，把原始 HMI 字段放进 `bindings.hmi_import`，并保留已知事件槽位。
未知对象类型不会被静默丢掉，而是转成可见的 text placeholder。这个能力只用于
反向查看和继续编辑，不声称 `.HMI` 无损往返、TFT 等价重建、完整资源/字库恢复或
实机显示证明。

导入官方 `.HMI` 后，可以先跑一次往返诊断，把还缺什么明确写出来再交给 Agent：

```powershell
python -m usarthmi --json hmi roundtrip-check path\to\project.HMI `
  --out-dir reverse_usarthmi\roundtrip_project `
  --source-tft path\to\official.run `
  --overwrite
```

它会写 `source.inspect.json`、`scene.imported.json`、
`regenerated\output.hmi`、`regenerated.inspect.json` 和
`roundtrip_report.json`。报告会比较源文件和再生成 HMI 的对象、资源、事件脚本数量
以及 SHA256；只有真实字节一致时才会把 `summary.byte_perfect` 置为 `true`，并且
始终保持 `safe_to_flash=false`。提供 `--source-tft` 时，它还会写
`event_index.inspect.json`，并把编译后 event-index/scheduler blocker 合并进
roundtrip 报告。桌面 EXE 里也有同样的 `Roundtrip HMI` 按钮，会把导入后的
scene、预览、agent context 和 blocker 摘要载回工作区。

## donor HMI fixture factory

当前如果要生成可被官方低层入口接受的 `.HMI` fixture，推荐路线不是“从零写完整
HMI writer”，而是基于官方 donor / template 的 patch factory。

当前稳定入口：

- CLI：`python -m usarthmi --json hmi donor-patch ...`
- API：`usarthmi.api.patch_hmi_donor_file(...)`
- 实现：`usarthmi.hmi_donor_patch`
- 官方低层 gate：`tools/official_hmi_lowlevel_probe.py`

这条路线的核心是保留 donor `.HMI` 的容器 / shadow-page 形状，只改目标页对象，
然后用官方 `open-lowlevel` / `compile-lowlevel` 验证输出。

当前边界：

- 支持目标：稳定、可复现、可验证的 donor-based `add/delete/move/set-int/set-str`
- 不声称：通用 from-scratch HMI writer
- 不声称：仅凭 low-level acceptance 就等于 runtime / 实机通过
- 不声称：授权绕过、DRM 绕过、官方 EXE/DLL patch

当前 corpus 在：

- `reverse_usarthmi/hmi_donor_lowlevel_probe_20260522`

建议先看：

- `donor_patch_capability_matrix.md`
- `donor_patch_capability_summary.json`
- `lowlevel_compatible_control_map.json`
- `reopen_safe_control_map.json`
- `fixture_corpus/corpus_manifest.json`

当前重要口径：

- 当前 exact donor `case42/43/44/80/83/85` 都能过 low-level gate
- 但仍保留一条历史 `case80` exact failed 记录，说明 donor revision / container
  shape 不能混为一谈
- 如果要一个稳定的 case80-like generated sample，优先用
  `case80_like_from_case83_delete_b1`

当前建议使用的静默兼容生成入口：

- `python tools\generate_lowlevel_compatible_fixture.py <control_type> --out-dir <dir>`
- `python -m usarthmi --json hmi lowlevel-compatible-fixture <control_type> --out-dir <dir>`
- `usarthmi.hmi_donor_patch.generate_lowlevel_compatible_fixture(...)`

如果你的目标是“按控件类型生成一个当前可证明能通过 official open-lowlevel /
compile-lowlevel 的修改后 HMI”，优先走这条 `lowlevel-compatible` 入口；它不把
GUI reopen 结果混进主门槛，也不会把“未跑 reopen”伪装成“已验证 reopen”。

当前建议使用的 reopen-safe 生成入口：

- `python tools\generate_reopen_safe_fixture.py <control_type> --out-dir <dir>`
- `python -m usarthmi --json hmi reopen-safe-fixture <control_type> --out-dir <dir>`
- `usarthmi.hmi_donor_patch.generate_reopen_safe_fixture(...)`

如果你的目标是“按控件类型生成一个当前可证明能正确打开的修改后 HMI”，优先走这条
`reopen-safe` 入口，而不是直接自由组合 donor-patch spec。

给动态快照 Goal A 喂样本时，只用 summary 里
`dynamic_snapshot_goal_a_ready=true` 的 fixture。

如果要做类似官方编辑器 `Compile` 的离线一键检查，用 `scene export`：

```powershell
python -m usarthmi --json scene export examples\polished_dashboard_demo\scene.json `
  --out-dir reverse_usarthmi\export_bundle `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --baseline-tft "C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft"
```

它一定会写 `export_report.json` 和 preview/agent 产物；提供 seed HMI 时会尝试
生成 `output.hmi`，同时提供兼容 baseline TFT 且 writer guard 通过时才会尝试生成
`output.tft`。当 `output.tft` 真正生成时，bundle 现在还会顺手写出
`smoke.expect.json`，并在 manifest/report 里给出原生 `scene smoke` 推荐命令，
减少下一步 live runtime 验证时再手工拼
expectation 文件。被跳过或阻止的 TFT 构建会写进报告，不会伪装成可烧录证明。
这个导出不会打开 COM36，也不会上传。

如果某个 scene 需要的不只是简单读回或 `printh` marker，而是更复杂的运行时
步骤，例如方法调用、点击后的状态变化、等待时间或文件系统准备，可以直接把
显式配方写进 `project.live_smoke`。当前建议的分工是：

- 自动生成：稳定 readback，加上简单 button/down/up -> `printh` marker
- `project.live_smoke`：方法调用、副作用验证、`wait`、文件准备和其他复杂
  runtime 序列

现在 `scene validate` / `scene check` 也会直接校验这块 schema，所以像缺
`command`、乱写 key、`attempts` 非法这类错误会在 scene 合约层就被拦下来，
不会拖到后面的 smoke 阶段才暴露。

如果想走一条 scene 驱动的 offline-to-live 入口，正式 CLI 入口是：

```powershell
python -m usarthmi --json scene smoke `
  examples\advanced_direct_tft_demo\data_record_text_select_button_case83_event_scene.json `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --baseline-tft "C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft" `
  --out reverse_usarthmi\caseC4_scene_smoke_cli
```

如果只是更习惯直接跑脚本，旧的 wrapper 也还在：

```powershell
python tools\scene_smoke_runner.py `
  --scene examples\advanced_direct_tft_demo\data_record_text_select_button_case83_event_scene.json `
  --seed "D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI" `
  --baseline-tft "C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft" `
  --out reverse_usarthmi\caseC4_scene_smoke_runner
```

这两个入口默认都会 build scene、自动解析同目录生成的 `smoke.expect.json`，并返回离线
`readiness` 摘要。再加 `--preflight` 可以做串口健康预检；加
`--smoke --upload` 则会继续跑 live runtime 检查，仍然复用同一份生成出来的
smoke bundle。

为了继续消灭 parallel truth，`scene smoke` 现在还支持：

- `--check-expect[=<path>]`：比较 scene 生成的 payload 和现有 legacy
  `smoke.expect.json` 是否一致
- `--write-expect[=<path>]`：用 scene 生成的 payload 回写 legacy
  `smoke.expect.json`

如果不显式给 path，会按约定俗成的 sibling 路径去找，例如
`*_scene.json -> *_smoke.expect.json`。

如果想看目录级别的收敛状态，可以跑：

```powershell
python tools\scene_smoke_migration_audit.py `
  --out examples\advanced_direct_tft_demo\live_smoke_migration_audit_2026-05-20.json
```

它会汇总：

- 多少 scene 已经声明 `project.live_smoke`
- 多少 legacy sibling `smoke.expect.json` 还存在
- 这些 legacy 文件里有多少已经和 scene 生成 payload 完全一致
- 哪些 legacy `smoke.expect.json` 已经变成 orphan

事件脚本现在可以走 scene 模型层读写，也会进入 agent context：

```powershell
python -m usarthmi --json scene new examples\new_project\scene.json --name NewProject
python -m usarthmi --json scene save-as examples\new_project\scene.json examples\new_project\scene_copy.json
python -m usarthmi --json scene events list examples\event_demo\scene.json --non-empty
python -m usarthmi --json scene events lint examples\event_demo\scene.json
python -m usarthmi --json scene events graph examples\event_demo\scene.json
python -m usarthmi --json scene events snippets
python -m usarthmi --json scene events set examples\event_demo\scene.json page0.evtbtn.up --line "printh 23 02 55 50"
python -m usarthmi --json scene events append-command examples\event_demo\scene.json page0.evtbtn.up --command vis --target status0 --value 1
python -m usarthmi --json scene events commands list examples\event_demo\scene.json page0.evtbtn.up
python -m usarthmi --json scene events commands replace examples\event_demo\scene.json page0.evtbtn.up --index 0 --command page --target page1 --dry-run --simulate --out-dir reverse_usarthmi\event_patch
python -m usarthmi --json scene events set examples\event_demo\scene.json page0.evtbtn.up --from-file event.txt
python -m usarthmi --json scene simulate examples\event_demo\scene.json page0.evtbtn.up --out-dir reverse_usarthmi\event_sim
python -m usarthmi --json scene scenario run examples\event_demo\scene.json examples\event_demo\scenario_printh.yaml --out-dir reverse_usarthmi\scenario
python -m usarthmi --json tft event-index inspect --hmi path\to\source.HMI --tft path\to\official.run --out reverse_usarthmi\event_index.json
python -m usarthmi --json tft event-index batch path\to\case_root --out reverse_usarthmi\event_index_batch.json
python -m usarthmi --json editor audit
```

这只是已知事件槽位（`load/loadend/down/up/unload/timer/slide`）的工程编辑和
agent 交接能力。事件 lint 能识别一小组受控命令
`page/ref/vis/tsw/click/get/set/printh/delay`，保留未知 raw 行，并输出页面/
对象引用诊断和跳页图，方便 agent 判断重命名或改逻辑会不会断引用。它不等价于
完整复刻官方事件编译器；只有有 fixture、字节码或活屏证据的事件路径才按对应级别
声明可编译或运行。
`scene events append-command` 是给 Agent 用的结构化命令追加入口，可以追加
`page`、`vis`、`tsw`、`click`、`set`、`printh`、`delay` 等受控命令，
不用让 Agent 手写事件源码格式。
`scene events commands` 是更细的命令级 patch 入口：Agent 可以
list/insert/replace/delete/move 单条事件命令，先要 dry-run diff，也可以顺手跑
before/after 离线模拟；dry-run 不写 scene，也不会碰 COM36。

`editor audit` 是当前“仿官方编辑器”目标的完成度清单；它会列出桌面
EXE、项目/页面、控件、布局、Agent 交接、导入导出已经实现的面，也包含一份
prompt-to-artifact 清单方便 agent 继续接手；事件逻辑仍保持标记为受控子集，
直到官方编译器/调度器等价性有证据为止。

`scene simulate` 是同一受控命令子集的离线执行器：它会输出当前页、控件属性、
可见性、触摸开关状态、模拟延时和 `printh` 结果，并可写
`runtime_trace.json`、`runtime_state.json`、`simulation_report.json` 给 agent
检查脚本改动。它不打开串口、不烧录、不证明官方调度器/字节码/物理触摸/真实时序/
媒体或文件系统副作用。
模拟器也补了一个小的官方脚本赋值表达式子集，覆盖裸 `sys0=28*5`、对象到对象赋值、
字符串拼接，以及字符串/数字 `+=` 更新，方便 agent 离线检查逻辑。
`scene scenario run` 在模拟器上加了多步回归脚本：YAML/JSON 里可以先触发事件槽，
再断言 `current_page`、`elapsed_ms`、`printh_hex`，或 `page0.num0.val` 这类控件
路径。它会写 `scenario_report.json` 和运行 trace/state，但仍然只做离线检查。
`tft event-index inspect` 是只读的编译后 TFT 证据入口：它会把 HMI 源事件槽位和
官方/生成 `.tft`/`.run` 里的 event table、callback slot 候选、post-primary
page-load chunk 放到同一个 JSON 里，用来继续缩小 scheduler/index/flags 缺口，
并始终保持 `safe_to_flash=false`。对于多页面 HMI fixture，它现在还会输出
`all_page_summary` 和压缩后的 `additional_pages`，覆盖非 `0.pa` 页面资源；
这些附加页面只扫描非空事件块，所以键盘页/辅助页会留下有用的 event match 和
未支持字节码样例，但不会变成空事件表搜索噪声。
`tft event-index batch` 会扫描 HMI 文件或 case 目录，优先匹配邻近的官方编译输出，
汇总哪些 fixture 还缺 event-index oracle 或完整 scheduler 证据，方便 agent 接手。
当前 case 38/41/42/43/44 的高级控件批量证据写在
`examples/event_index_batch_3841424344_2026-05-18.json`；里面同时列出
scheduler 分类以及剩余的字节码/调度 blocker。其中 case 38 选择文本和
case 41 滑动文本的对象事件字节码已经和官方 TFT event table 字节匹配，并作为
`object_callbacks_only` complete probe 记录。case 42 数据记录源码事件现在也能编译，
并且 `data0/b0/b1/b2/b3` 对象事件表已经和官方 TFT 字节匹配；剩下的是 page-load
里的 `repo` 路径还没有 page callback/scheduler 证明。`event-index inspect` 现在会记录
官方 page-load `repo` 命令候选：`0x70B` 处的 `09 18 08 01 e5 00 00 00`，
方便下一轮继续缩小命名空间/调度缺口。case 43/44 的可见文件启动脚本
已经能按 `findfile/newfile/if/page` 源码流程编译，但官方 TFT 后面仍追加了未恢复的
隐藏 unload/runtime callback。`page_event_prefix_probe` 现在记录到它们的可见
page-event 前缀都在 `0x2348` 字节匹配，并把紧跟在 unload 后的 immediate hidden item
单独标成 `0xBF()` 无参 method call；后续 complete-item preview 里能解出
`"当前路径：" + field 0x89` 赋值表达式、`btnOpenFile/btnRenameFile/btnDelFile`
显隐切换，以及 `spstr fbrowser0.txt,t0.txt,".",1` 到 field slot `0x8E -> 0x207`
的结构化解码。同一个 `spstr` 形态现在也能按 case43/44 的 file-storage page slot-width
规则编译回官方 payload；UTF-8 的 `fbpath.txt="当前路径："+fbrowser0.dir` 表达式也已覆盖。
`if(fbrowser0.txt!="")` 也会解码/编译为官方的 `if_field_ne` 形态。
field+field 路径拼接、`delfile` opcode 形态、几个 page-qualified helper slot，
`btlen` opcode、无 `else` 的 `if(field<field)`、`&txt&` / `&id&` 当前对象占位符、
`dp` 操作数，以及官方 file-open 分支脚本的精确 fixture 也已经在观察到的形态上固定。
case43 和 case44 的 `2.pa`/`main` 页现在 11 个对象事件全部写进 batch 报告并能和官方
TFT 字节匹配，main 页 compile error 为 0；批量 all-page 统计现在是 `27095` 个
compiled event-table match，剩余 helper page compile error 为 `85`。callback/runtime
绑定仍未恢复，所以还不是完整 scheduler/runtime 证明。

case51 的最小事件调度 oracle 已经整理到
`C:\Users\SinYu\Desktop\case_for_codex\case_51_scheduler_minimal_oracle`。
它包含 page0 load/loadend、button down/up、timer tick、page1 load 四组官方
源 HMI 和完整 `output/source_raw.tft`。主仓库里的 `examples\case51_*.json`
已经记录：page0 load phase `0x327`，button table `0x18B` / first executable
`0x197`，timer table `0x1C7` / first executable `0x1D4`，page1 load phase
`0x45A`，附加页 `global_slot_offset=149`，`page1.t0.txt` 官方 field slot
`0xD2`。page-load phase descriptor 现在会保留 phase 前 64 字节和后 512 字节上下文，
并扫描 phase start / first executable / phase end 的 LE32 引用；page0 `0x327` 和
page1 `0x45A` 目前都没有 object-region 内的 LE32 dispatch 引用命中。这些只证明
官方编译器 oracle 和附加页 slot 规则；primary page-load 现在能定位到
`event_offset_0x34` 指向的 page event-table 边界，但 page lifecycle callback
入口仍未证明，所以继续保留 `SCHEDULER_RUNTIME_EQUIVALENCE_UNPROVEN`。

case52 的 lifecycle-delta oracle 也已经补齐 6 组官方 GUI 保存 HMI +
完整官方 TFT，位置在
`C:\Users\SinYu\Desktop\case_for_codex\case_52_page_lifecycle_delta_oracle`。
主仓库 `examples\case52_*.json` 记录：page0 load/loadend phase 都稳定在
`0x2AB`；load+loadend 是一个 merged phase，prefix length `47`；长 body
把 prefix length 推到 `50`，但这些 page0 phase 仍没有直接 LE32 dispatch 引用。
同 payload 放进 button up 时走已知 object callback table：`0x18B` /
first executable `0x1A1` / `slot_0x10`。clean page1 load candidate 在 `0x255`，
并出现一个 `prefix_end` 引用 `0x1AEB`；但
`examples\case52_lifecycle_dispatch_candidates_20260518.json` 显示被引用的
`0x272` 同时也是 primary `page0/t0/bar1` 的 `event_table_start`。这个别名风险
说明它只能作为编译器 oracle 候选，不能当 runtime scheduler 证明。
同一个报告现在还会输出 `lifecycle_record_fields`：case51+case52 的 page-load
oracle 里，page record 的 callback slots `0x0c/0x10/0x14` 都保持
`0xFFFFFFFF`，而 `event_offset_0x34` 指向 page event-table 边界；clean
case52-06 里它等于 `0x272` phase-end/wrapper 边界。合并报告
`examples\case51_case52_lifecycle_dispatch_candidates_20260518.json` 把这个负证据
和 button/timer object callback 的 first-executable 指针对照放在一起。
当前本地 scene-to-TFT 最小 page0 load writer 已实机通过：生成的
`reverse_usarthmi\case52_page0_load_local_build_probe_20260518_v2\output.tft`
把 `printh AA 52 10 01` 放进 `post_primary_page_event` phase，COM36 烧录后
`page 0` 返回 raw `AA 52 10 01`，证据记录在
`examples\lifecycle_runtime_smoke\page0_load_local_generated_verified_2026-05-18.json`。
这只覆盖当前最小 page0 load 形状，不代表任意 lifecycle 脚本或 page1 lifecycle
调度已经恢复。

控件对象也可以用 headless 命令做 agent 交接：

```powershell
python -m usarthmi --json scene assets list examples\event_demo\scene.json
python -m usarthmi --json scene assets add examples\event_demo\scene.json logo --source assets\logo.png
python -m usarthmi --json scene assets update examples\event_demo\scene.json logo --normal assets\logo-normal.png
python -m usarthmi --json scene assets delete examples\event_demo\scene.json logo --force
python -m usarthmi --json scene project update examples\event_demo\scene.json --name EventDemo --default-page page0 --background-color 65535
python -m usarthmi --json scene pages add examples\event_demo\scene.json page1
python -m usarthmi --json scene pages update examples\event_demo\scene.json page1 --id settings --layout-json '{\"type\":\"absolute\"}'
python -m usarthmi --json scene pages duplicate examples\event_demo\scene.json page0 --id page2
python -m usarthmi --json scene pages delete examples\event_demo\scene.json page2
python -m usarthmi --json scene widgets update examples\event_demo\scene.json page0.evtbtn --x 40 --text "Run" --resource asset=logo
python -m usarthmi --json scene widgets copy-to examples\event_demo\scene.json page0.evtbtn page0 --id evtbtn_paste
python -m usarthmi --json scene widgets duplicate examples\event_demo\scene.json page0.evtbtn --id evtbtn_copy
python -m usarthmi --json scene widgets duplicate examples\event_demo\scene.json page0.evtbtn --id evtbtn_copy2
python -m usarthmi --json scene widgets cut examples\event_demo\scene.json page0.evtbtn_paste
python -m usarthmi --json scene widgets move examples\event_demo\scene.json page0.evtbtn_copy --direction up
python -m usarthmi --json scene design align examples\event_demo\scene.json page0.evtbtn page0.evtbtn_copy --edge left --anchor first --out-dir reverse_usarthmi\design_session
python -m usarthmi --json scene design distribute examples\event_demo\scene.json page0.evtbtn page0.evtbtn_copy page0.evtbtn_copy2 --axis horizontal --out-dir reverse_usarthmi\design_session
python -m usarthmi --json scene design match-size examples\event_demo\scene.json page0.evtbtn page0.evtbtn_copy --mode width --anchor first --out-dir reverse_usarthmi\design_session
python -m usarthmi --json scene widgets delete examples\event_demo\scene.json page0.evtbtn_copy
python -m usarthmi --json scene widgets delete examples\event_demo\scene.json page0.evtbtn_copy2
python -m usarthmi --json scene design move examples\event_demo\scene.json page0.evtbtn --x 80 --y 96 --out-dir reverse_usarthmi\design_session
python -m usarthmi --json scene design resize examples\event_demo\scene.json page0.evtbtn --w 140 --h 48 --out-dir reverse_usarthmi\design_session
```

`scene design` 是 GUI 画布交互用的同一条写入路径：它会修改 scene 坐标/尺寸，
也能按边或中心线对齐多个控件、均匀分布三个以上控件、统一宽高/尺寸，同时在输出目录写 `design_session.json`、`agent_patch.json` 和
`scene.modified.json`，方便 agent 审核或回放；它不构建 TFT，也不烧录。

需要双击打开时，用 `dist\usarthmi-preview.exe`。它现在是官方编辑器风格的
Windows 外壳：左侧对象树，中间画布预览和 agent 标注层，右侧 inspector、
Project/Page 设置、基础 Properties 表单、Toolbox 添加控件表单、diagnostics、
带命令片段和 `Save+Simulate` 离线事件 trace 的事件编辑，以及 agent 产物面板。顶栏 Undo/Redo 可以回退或重做 GUI 写入 scene 文件的编辑。对象树可以新增/复制/删除页面，复制/剪切/粘贴/删除控件，也可以
上移/下移/置顶/置底控件层级；多选同页控件后可以 Align Left、Align Top、H Center、V Center、Dist H、Dist V、Same W、Same H、Same Size。
选中页面后点 `Preview Page` 会按该页面重新生成预览包；选中控件后点 Preview Bundle 会预览该控件所在页面。
对象树或预览画布获得焦点时，`Delete` 会删除选中控件，`Ctrl+C`/`Ctrl+X`/`Ctrl+V` 会复制、剪切、粘贴控件，`Ctrl+D` 会复制出副本。
Project 页可以改项目名、默认页、画布宽高/背景、页面 ID 和
页面 layout JSON；页面重命名只改 scene，并会提示事件脚本里仍引用旧页名的位置。
控件重命名也会提示同页事件脚本里仍引用旧控件 ID 的位置；显式勾选/传入
`--rewrite-event-references` 时可以同步改写这些引用。
Assets 面板可以新增/更新/删除 scene 图片资源；资源仍被控件引用时默认阻止删除，
除非显式强制。Properties/Toolbox 既能改 `id/type/x/y/w/h/text/value`，也能用
JSON 改 `style/resources/bindings`；Toolbox 的 `Load Template` 会按控件类型填入
较合理的初始尺寸、文字、值和资源/样式 JSON。它修改 scene 文件并重新生成 preview/context；
顶部按钮可以新建空白 scene、导入官方 `.HMI` 成 scene/report/preview 包，或把
当前 scene 另存为新路径。中间预览画布可以点选控件、拖动移动、拖右下角缩放，
也可以用方向键微调选中控件；拖拽/缩放/布局编辑会使用预览工具栏里的 Snap 值，
并在输出目录留下 agent patch，对象树对齐/分布/统一尺寸也走同一条 design patch 路径。点
`Check Scene` 会跑离线诊断和事件模拟报告；点 `Export Bundle` 会跑离线编译式报告；点 `Build TFT` 可以额外构建 HMI/TFT，但
仍然不会上传。

## 常用串口命令

```powershell
python -m usarthmi --json connect --port COM36 --baud 9600
python -m usarthmi --json sendme --port COM36 --baud 9600
python -m usarthmi --json get t0.txt --port COM36 --baud 9600
python -m usarthmi --json set t0.txt '"hello"' --port COM36 --baud 9600
python -m usarthmi --json dim 30 --port COM36 --baud 9600
```

烧录 TFT 建议使用全量串口上传，慢一点，但更稳：

```powershell
python -m usarthmi --json tft readiness `
  --file output.tft

python -m usarthmi --json tft upload `
  --file output.tft `
  --port COM36 `
  --baud 9600 `
  --download-baud 921600 `
  --skip-if-current `
  --verify-after-upload `
  --verify-get t0.txt=nihao `
  --verify-get b0.txt=ceshi `
  --verify-step '{"command":"sendme","expected_kind":"page_id","expected_value":0}' `
  --verify-capture `
  --progress
```

`tft readiness` 是纯离线入口：它会检查 TFT checksum，并在旁边存在
`manifest.json` 时，把 `delivery_status`、`oracle_alignment`、
`hardware_quarantine` 以及当前是否还有 SD 恢复阻塞一起报出来。只想先判断
“这份 build 产物现在该不该考虑上板”时，优先用它。

成功上传后，CLI 会原子写入 `.usarthmi_last_upload.json`。下次带
`--skip-if-current` 上传时，会用候选 TFT 的 SHA256/大小，加上端口、
波特率和目标型号，对比这份“本工具上次成功上传”记录；匹配时会跳过运行时预检
和实际上传。注意它只代表本工具上次传过什么，不证明屏幕没有被 SD 卡、官方
下载器或另一台机器改过。

如果 build manifest 里声明了 `hardware_quarantine.active=true`，那么上传和
live smoke 默认会被拦住，即使 checksum / 型号预检本来能通过。只有在已经有
明确的恢复/实机计划时，才用 `--allow-hardware-quarantine` 显式放行。
旧的 `--allow-quarantined-touch-capture` 仍保留兼容，但后续通用 override
请优先用新的硬件隔离开关。

需要“烧完就验”时加 `--verify-after-upload`。它会在上传成功或
`--skip-if-current` 命中后重新跑串口健康检查，并按 `--verify-get`
读回对象属性；验证失败时命令返回非零，也不会把这次结果写成新的
known-current manifest。

如果烧完后还需要执行一串运行时动作，用可重复的 `--verify-step`。它可以接
裸命令，也可以接 JSON，例如 `{"command":"sendme","expected_kind":"page_id","expected_value":0}`。
常见读回/点击检查可以用更短的写法：`get numval.val => 124` 或
`click incbtn,1 => hex:23 02 4e 31`。媒体类验证可以先执行
`{"command":"wav0.en=1","expect_response":false}`，再用
`{"command":"get wav0.en","expected_kind":"number","expected_value":1}` 做读回确认。

如果视觉状态也要留证据，再加 `--verify-capture`。默认会用这台机器上更稳的
MSMF 摄像头路径，把照片存到 `reverse_usarthmi/upload_verify_captures/`。

## TSW 真实触摸证明

`examples/number_demo/tsw_promotion_scene.json` 已经有 isolated TSW PROMOTION
页面和串口 click 负结果。真实手指触摸不要再用临时监听脚本，直接跑：

```powershell
python tools\tsw_physical_touch_proof.py `
  --out reverse_usarthmi\number_demo_tsw_promotion_gb2312font_20260516\physical_touch_proof_live.json
```

这个 runner 会先弹出 `tools/wait_user_ack.ps1` 的置顶确认窗口。你点
“继续”后才会打开 COM36，并且会先确认当前页面 `title.txt` 是
`TSW PROMOTION`；错页面会直接退出，不会让你白按。屏幕标题会依次提示：

- `TAP TARGET`：按一次 TARGET，抓到 baseline TG 才继续。
- `TRY TARGET`：runner 已经执行 DISABLE，只在这个窗口里试按 TARGET。
- `TAP AGAIN`：runner 已经执行 ENABLE，再按一次 TARGET 验恢复。

成功条件很窄：baseline 有 TG、disabled 窗口没有 TG、恢复后有 TG，并且
T0/T1 状态 marker 都到达。退出码含义：

- `0`：完成并证明 `physical_touch_lockout_live_observed=true`。
- `1`：跑完但没有形成禁触证明。
- `2`：弹窗取消或超时，没有用户确认。
- `3`：baseline 没抓到 TG，未进入 disable 阶段。
- `4`：页面不是预期的 TSW PROMOTION。

只想检查流程而不碰串口，可以用：

```powershell
python tools\tsw_physical_touch_proof.py --dry-run
```

## 场景构建示例

只做预览：

```powershell
python -m usarthmi --json scene preview examples\menu_demo\scene.json --out preview.png
python -m usarthmi --json hmi import path\to\lcd_test.HMI --out-dir hmi_import --overwrite
```

构建外部图片 demo：

```powershell
python -m usarthmi --json scene build examples\external_picture_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --baseline-tft C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft `
  --out reverse_usarthmi\external_picture_demo_build
```

构建媒体 authoring demo：

```powershell
python -m usarthmi --json scene build examples\media_widgets_demo\scene.json `
  --seed D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI `
  --out reverse_usarthmi\media_widgets_demo_build
```

更多示例见 [SCENE_BUILDER.md](SCENE_BUILDER.md) 和 [examples/README.md](examples/README.md)。

## 本地参考仓库说明

开发机里可能会看到 `github_refs/`、`github_tjc_screen_for_codex/`、`external/` 这类目录。它们是逆向时用过的本地参考 clone 或第三方工具，不是主仓库的一部分。

当前 `.gitignore` 已经排除了这些目录，避免把外部仓库、官方资源、生成产物和大文件误提交进来。

## 开发建议

```powershell
python tools\run_smoke.py
python tools\run_acceptance.py
python tools\run_official_probe_tests.py
python tools\run_full_tests.py
```

测试分层约定：

- `smoke`：日常默认，只跑快速离线回归，目标控制在 30 秒到 2 分钟。
- `acceptance`：收尾/交付前跑，覆盖 smoke，再加 donor patcher 验收、donor summary JSON、static/dynamic index 基础结构检查。
- `official_probe`：显式触发，只有在你改了官方工具 probe 相关代码，或者确实要验证官方 GUI / low-level probe 集成时才跑。
- `full`：重大变更时跑的大回归；它会覆盖普通测试面，但 `official_probe` 仍然默认保持跳过，除非你明确打开。

如果你确实要把 full 和 official probe 一起跑：

```powershell
python tools\run_full_tests.py --include-official-probe
```

手动 marker 入口：

```powershell
python -m pytest -m smoke
python -m pytest -m acceptance
python -m pytest -m official_probe --run-official-probe
python -m pytest -m full
```

推荐给 agent / 日常开发的默认动作：

- 日常修改后先跑 `python tools\run_smoke.py`
- 收尾前跑 `python tools\run_acceptance.py`
- 只有真的在碰官方 probe 这条线时才跑 `python tools\run_official_probe_tests.py`
- 没有重大变更时，不要顺手跑 `full`

部分测试依赖本地 fixture，没有对应文件时会自动跳过。给项目加新控件时，最好同时补：

- 最小 scene 示例。
- 对应 fixture 或分析说明。
- 单元测试或字节对齐测试。
- 如果能烧录，补串口读回或摄像头验证记录。

## 风险提示

这是逆向项目，不是官方 SDK。生成的 TFT 在新型号、新分辨率、新资源布局上都应该先做小样例验证。实机烧录前建议先跑 `tft checksum`，并准备一个已知可恢复的 TFT。
