from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import official_gui_host_select  # noqa: E402
from usarthmi.official_gui_automation import resolve_official_gui_control  # noqa: E402


SCHEMA_VERSION = 1
DEFAULT_PAGE_RESOURCE = "0.pa"

HOOK_FUNCTIONS = {
    "open_project": 'HMIFORM.main.filecaozuo("open", hmi_path)',
    "select_page": "HMIFORM.main.pageadmin1.selectindex(page_index)",
    "add_page": "Myapp.Creatnewpage(true) + ResourcesPages.Add(...) + RefpageID() + pageadmin1.RefList()/selectindex()",
    "select_object": "TFTEDIT.TFTEDIT.setxuanzhong_add(object_index) + HMIFORM.main.objselect()",
    "create_control": "HMIFORM.main.AddObj(hmitype.AppData.appobjs.<control>)",
    "patch_field": "hmitype.mpage.changobjattch(object_index, field, value)",
    "patch_event": "HMIFORM.main.objatt1.attload(...) + SaveCodes()",
    "save": 'HMIFORM.main.filecaozuo("save", "")',
    "dump_page": "hmitype.myapp.OutPutPageFile(dpage, null, page_dump_path, false)",
    "compile_tft": "hmitype.appbianyi.FileBianyi(myapp, output_tft, log, CompileMode.OutPutTFT)",
}


def normalize_hook_script(payload: dict[str, Any]) -> dict[str, Any]:
    hmi_path = Path(str(payload["hmi_path"])).resolve()
    out_dir = Path(str(payload.get("out_dir") or hmi_path.parent / "official_hook_runner")).resolve()
    page_index = int(payload.get("page_index", 0))
    page_resource = str(payload.get("page_resource") or DEFAULT_PAGE_RESOURCE)
    report_path = Path(str(payload.get("report_path") or out_dir / "hook_host_report.json")).resolve()
    install_dir = None if payload.get("install_dir") in (None, "") else Path(str(payload["install_dir"])).resolve()

    object_index = payload.get("object_index")
    object_name = payload.get("object") or payload.get("object_name")
    create_control = payload.get("create_control")
    add_page_name = None if payload.get("add_page_name") in (None, "") else str(payload["add_page_name"])
    patch_fields: list[tuple[str, str]] = []
    patch_events: list[tuple[str, list[str]]] = []
    force_save = bool(payload.get("save", False))
    force_page_dump = bool(payload.get("dump_page", False))
    compile_output_path = None
    requested_mode = _normalize_kind(payload.get("mode"))
    single_session = bool(payload.get("single_session", False)) or requested_mode in {
        "macro",
        "single-session",
        "single-session-macro",
    }
    macro_lines: list[str] = []
    plan: list[dict[str, Any]] = [
        {"kind": "open-project", "official_function": HOOK_FUNCTIONS["open_project"]},
    ]

    actions = list(payload.get("actions") or [])
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError(f"action must be an object: {action!r}")
        kind = _normalize_kind(action.get("kind"))
        if kind == "select-page":
            page_index = int(action.get("page_index", page_index))
            page_resource = str(action.get("page_resource") or page_resource)
            if single_session:
                macro_lines.append(
                    "\t".join(
                        [
                            "select-page",
                            _macro_field(page_index),
                            _macro_field(page_resource),
                        ]
                    )
                )
            plan.append(
                {
                    "kind": kind,
                    "page_index": page_index,
                    "page_resource": page_resource,
                    "official_function": HOOK_FUNCTIONS["select_page"],
                }
            )
        elif kind == "add-page":
            add_page_name = str(action.get("name") or action.get("page_name") or action.get("pagename") or "")
            if not add_page_name:
                raise ValueError("add-page requires name/page_name/pagename")
            page_resource = str(action.get("page_resource") or page_resource)
            if single_session:
                macro_lines.append("\t".join(["add-page", _macro_field(add_page_name)]))
            plan.append(
                {
                    "kind": kind,
                    "name": add_page_name,
                    "page_resource": page_resource,
                    "official_function": HOOK_FUNCTIONS["add_page"],
                }
            )
        elif kind == "select-object":
            object_name = action.get("object") or action.get("object_name") or object_name
            object_index = action.get("object_index", object_index)
            macro_object_index = object_index
            if single_session:
                if macro_object_index is None:
                    if object_name in (None, ""):
                        raise ValueError("macro select-object requires object_index or object")
                    macro_object_index = official_gui_host_select.resolve_object_index(
                        hmi_path=hmi_path,
                        page_resource=page_resource,
                        object_name=str(object_name),
                    )
                macro_lines.append("\t".join(["select-object", _macro_field(macro_object_index)]))
            plan.append(
                {
                    "kind": kind,
                    "object": object_name,
                    "object_index": object_index,
                    "official_function": HOOK_FUNCTIONS["select_object"],
                }
            )
        elif kind == "create-control":
            create_control = action.get("control") or action.get("create_control") or create_control
            create_control_var = None
            if create_control not in (None, ""):
                create_control_var = resolve_official_gui_control(str(create_control)).decompiled_var_name
            if single_session:
                if not create_control_var:
                    raise ValueError("macro create-control requires control/create_control")
                macro_lines.append("\t".join(["create-control", _macro_field(create_control_var)]))
            plan.append(
                {
                    "kind": kind,
                    "control": create_control,
                    "control_var_name": create_control_var,
                    "official_function": HOOK_FUNCTIONS["create_control"],
                }
            )
        elif kind == "patch-field":
            field = str(action["field"])
            value = str(action.get("value", ""))
            patch_fields.append((field, value))
            if single_session:
                macro_lines.append(
                    "\t".join(
                        [
                            "patch-field",
                            _macro_field(field),
                            _macro_field(value),
                        ]
                    )
                )
            plan.append(
                {
                    "kind": kind,
                    "field": field,
                    "value": value,
                    "official_function": HOOK_FUNCTIONS["patch_field"],
                }
            )
        elif kind == "patch-event":
            event_name = str(action.get("event") or action.get("event_name"))
            lines = [str(line) for line in action.get("lines", [])]
            patch_events.append((event_name, lines))
            if single_session:
                macro_lines.append(
                    "\t".join(
                        [
                            "patch-event",
                            _macro_field(event_name),
                            _macro_event_lines(lines),
                        ]
                    )
                )
            plan.append(
                {
                    "kind": kind,
                    "event": event_name,
                    "lines": lines,
                    "official_function": HOOK_FUNCTIONS["patch_event"],
                }
            )
        elif kind == "save":
            force_save = True
            if single_session:
                macro_lines.append("save")
            plan.append({"kind": kind, "official_function": HOOK_FUNCTIONS["save"]})
        elif kind == "dump-page":
            force_page_dump = True
            if single_session:
                macro_lines.append("dump-page")
            plan.append({"kind": kind, "official_function": HOOK_FUNCTIONS["dump_page"]})
        elif kind == "compile":
            compile_output_path = Path(str(action.get("output") or out_dir / "managed_compile.tft")).resolve()
            if single_session:
                macro_lines.append("\t".join(["compile", _macro_field(compile_output_path)]))
            plan.append(
                {
                    "kind": kind,
                    "output": str(compile_output_path),
                    "official_function": HOOK_FUNCTIONS["compile_tft"],
                }
            )
        else:
            raise ValueError(f"unsupported hook action kind: {action.get('kind')!r}")

    create_control_var_name = None
    if create_control not in (None, ""):
        create_control_var_name = resolve_official_gui_control(str(create_control)).decompiled_var_name
        object_index = -1

    if object_index is None and object_name in (None, ""):
        if patch_fields or patch_events:
            raise ValueError("patch-field and patch-event require select-object or create-control")
        object_index = -1

    return {
        "schema_version": SCHEMA_VERSION,
        "name": str(payload.get("name") or "official_hmi_hook_runner"),
        "hmi_path": str(hmi_path),
        "out_dir": str(out_dir),
        "page_index": page_index,
        "page_resource": page_resource,
        "object_index": None if object_index is None else int(object_index),
        "object_name": None if object_name in (None, "") else str(object_name),
        "create_control": None if create_control in (None, "") else str(create_control),
        "create_control_var_name": create_control_var_name,
        "add_page_name": add_page_name,
        "patch_fields": patch_fields,
        "patch_events": patch_events,
        "force_save": force_save,
        "force_page_dump": force_page_dump,
        "compile_output_path": None if compile_output_path is None else str(compile_output_path),
        "single_session": single_session,
        "macro_lines": macro_lines,
        "report_path": str(report_path),
        "install_dir": None if install_dir is None else str(install_dir),
        "plan": plan,
    }


def run_hook_script(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    normalized = normalize_hook_script(payload)
    out_dir = Path(normalized["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": "official_hmi_hook_runner",
        "name": normalized["name"],
        "dry_run": bool(dry_run),
        "status": "dry_run" if dry_run else "ok",
        "hmi_path": normalized["hmi_path"],
        "out_dir": normalized["out_dir"],
        "plan": normalized["plan"],
        "host_report_path": normalized["report_path"],
        "single_session": normalized["single_session"],
        "macro_lines": normalized["macro_lines"],
    }
    if dry_run:
        return report

    hmi_path = Path(normalized["hmi_path"])
    object_index = normalized["object_index"]
    if normalized["macro_lines"]:
        object_index = -1 if object_index is None else object_index
    elif normalized["object_name"] is not None:
        object_index = official_gui_host_select.resolve_object_index(
            hmi_path=hmi_path,
            page_resource=str(normalized["page_resource"]),
            object_name=str(normalized["object_name"]),
        )

    host_result = official_gui_host_select.run_probe(
        hmi_path=hmi_path,
        page_index=int(normalized["page_index"]),
        page_resource=str(normalized["page_resource"]),
        object_index=int(object_index),
        report_path=Path(normalized["report_path"]),
        patch_fields=list(normalized["patch_fields"]),
        patch_events=list(normalized["patch_events"]),
        create_control_var_name=normalized["create_control_var_name"],
        add_page_name=normalized["add_page_name"],
        macro_lines=list(normalized["macro_lines"]),
        compile_output_path=None
        if normalized["compile_output_path"] is None
        else Path(str(normalized["compile_output_path"])),
        force_save=bool(normalized["force_save"]),
        force_page_dump=bool(normalized["force_page_dump"]),
        install_dir=None if normalized["install_dir"] is None else Path(str(normalized["install_dir"])),
    )
    report["host_result"] = host_result
    report["host_returncode"] = host_result.get("returncode")
    report["host_report_json"] = host_result.get("report_json")
    report["page_dump_path"] = host_result.get("page_dump_path")
    report["compile_output_path"] = host_result.get("compile_output_path")
    if int(host_result.get("returncode", 1)) != 0:
        report["status"] = "failed"
    report_path = out_dir / "hook_runner_report.json"
    report["report_json"] = str(report_path.resolve())
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _normalize_kind(value: object) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _macro_field(value: object) -> str:
    text = str(value)
    return text.replace("\t", " ").replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


def _macro_event_lines(lines: list[str]) -> str:
    escaped_lines = []
    for line in lines:
        escaped_lines.append(str(line).replace("\t", " ").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n"))
    return "\\n".join(escaped_lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run clickless official USART HMI automation through in-process official function calls."
    )
    parser.add_argument("--script-json", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.script_json.read_text(encoding="utf-8-sig"))
    report = run_hook_script(payload, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"ok", "dry_run"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
