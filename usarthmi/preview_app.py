from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from .agent_preview import generate_agent_preview
from .api import build_scene_artifacts, get_widget_capability, list_widget_capabilities
from .design_ops import (
    design_align_widgets,
    design_distribute_widgets,
    design_match_size_widgets,
    design_move_widget,
    design_resize_widget,
)
from .event_logic import list_event_command_snippets
from .event_simulator import simulate_scene_event
from .export_bundle import export_scene_bundle
from .hmi_import import import_hmi_project
from .hmi_roundtrip import check_hmi_roundtrip
from .scene import load_scene
from .scene_check import check_scene_project
from .scene_edit import (
    EVENT_NAMES,
    add_scene_asset,
    add_scene_page,
    add_scene_widget,
    clear_scene_event,
    copy_scene_widget,
    cut_scene_widget,
    create_scene_document,
    delete_scene_asset,
    delete_scene_page,
    delete_scene_widget,
    duplicate_scene_page,
    duplicate_scene_widget,
    get_scene_event,
    list_scene_assets,
    move_scene_widget,
    paste_scene_widget,
    save_scene_document_as,
    set_scene_event,
    update_scene_asset,
    update_scene_page,
    update_scene_project,
    update_scene_widget,
)
from .widget_templates import get_widget_template


APP_TITLE = "USART HMI Agent Editor"
DEFAULT_SEED_HMI = Path(r"D:\MySTM32\H723ZGT6\Program\ISP_Test\lcd_test.HMI")
DEFAULT_BASELINE_TFT = Path(r"C:\Users\SinYu\Desktop\case_for_codex\case_00_baseline\lcd_test.tft")


def main() -> None:
    app = PreviewApp()
    app.run()


class PreviewApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("1240x780")
        self.root.minsize(1080, 680)
        self.queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.repo_root = _default_repo_root()
        default_scene = self.repo_root / "examples" / "polished_dashboard_demo" / "scene.json"
        default_out = self.repo_root / "reverse_usarthmi" / "gui_agent_preview"
        self.scene_var = tk.StringVar(value=str(default_scene if default_scene.exists() else ""))
        self.out_var = tk.StringVar(value=str(default_out))
        self.seed_var = tk.StringVar(value=str(DEFAULT_SEED_HMI if DEFAULT_SEED_HMI.exists() else ""))
        self.baseline_var = tk.StringVar(value=str(DEFAULT_BASELINE_TFT if DEFAULT_BASELINE_TFT.exists() else ""))
        self.target_var = tk.StringVar(value="TJC8048X543_011C")
        self.snap_var = tk.StringVar(value="4")
        self.preview_image: ImageTk.PhotoImage | None = None
        self.annotated_image: ImageTk.PhotoImage | None = None
        self.last_context: dict[str, Any] | None = None
        self.tree_payloads: dict[str, dict[str, Any]] = {}
        self.preview_display: dict[str, Any] = {}
        self.preview_drag: dict[str, Any] | None = None
        self.preview_temp_rect: int | None = None
        self.preview_overlay_ids: list[int] = []
        self.undo_stack: list[dict[str, str]] = []
        self.redo_stack: list[dict[str, str]] = []
        self.widget_clipboard: dict[str, Any] | None = None
        self._scene_history_path: str | None = None
        self._scene_history_snapshot: str | None = None
        self._scene_history_suspended = False
        self.undo_button: ttk.Button | None = None
        self.redo_button: ttk.Button | None = None
        self.selected_event_owner: dict[str, Any] | None = None
        self.selected_page_payload: dict[str, Any] | None = None
        self.selected_widget_payloads: list[dict[str, Any]] = []
        self.event_name_var = tk.StringVar(value="down")
        self.event_snippets = list_event_command_snippets()["snippets"]
        self.event_snippet_var = tk.StringVar(value=self.event_snippets[0]["label"] if self.event_snippets else "")
        self.event_target_var = tk.StringVar(value="Select a page or object")
        self.selected_widget_payload: dict[str, Any] | None = None
        self.property_target_var = tk.StringVar(value="Select an object")
        self.rewrite_widget_refs_var = tk.BooleanVar(value=False)
        self.property_vars = {
            "id": tk.StringVar(),
            "type": tk.StringVar(),
            "x": tk.StringVar(),
            "y": tk.StringVar(),
            "w": tk.StringVar(),
            "h": tk.StringVar(),
            "text": tk.StringVar(),
            "value": tk.StringVar(),
        }
        self.property_json_texts: dict[str, tk.Text] = {}
        self.toolbox_vars = {
            "page": tk.StringVar(value="page0"),
            "id": tk.StringVar(value="text1"),
            "type": tk.StringVar(value="text"),
            "x": tk.StringVar(value="40"),
            "y": tk.StringVar(value="40"),
            "w": tk.StringVar(value="160"),
            "h": tk.StringVar(value="48"),
            "text": tk.StringVar(value="Text"),
            "value": tk.StringVar(),
        }
        self.toolbox_json_texts: dict[str, tk.Text] = {}
        self.asset_payloads: dict[str, dict[str, Any]] = {}
        self.asset_vars = {
            "key": tk.StringVar(),
            "id": tk.StringVar(),
            "source": tk.StringVar(),
            "normal": tk.StringVar(),
            "pressed": tk.StringVar(),
            "disabled": tk.StringVar(),
        }
        self.project_vars = {
            "name": tk.StringVar(),
            "default_page": tk.StringVar(),
            "width": tk.StringVar(),
            "height": tk.StringVar(),
            "background_color": tk.StringVar(),
        }
        self.page_target_var = tk.StringVar(value="Select a page")
        self.page_vars = {"id": tk.StringVar()}
        self.page_layout_text: tk.Text | None = None
        self.widget_type_options = _widget_type_options()
        self._build_ui()
        self._load_scene_outline(silent=True)
        self.root.after(100, self._drain_queue)

    def run(self) -> None:
        self.root.mainloop()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        header = ttk.Frame(self.root, padding=(14, 12, 14, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="USART HMI Agent Editor", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Official-editor style workspace: object tree, canvas preview, diagnostics, agent artifacts, no implicit hardware upload.").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(3, 0),
        )

        paths = ttk.Frame(self.root, padding=(14, 0, 14, 8))
        paths.grid(row=1, column=0, sticky="ew")
        paths.columnconfigure(1, weight=1)
        paths.columnconfigure(4, weight=1)
        self._path_row(paths, 0, "Scene", self.scene_var, self._choose_scene, column=0)
        self._path_row(paths, 0, "Output", self.out_var, self._choose_output_dir, column=3)
        self._path_row(paths, 1, "Seed HMI", self.seed_var, self._choose_seed, column=0)
        self._path_row(paths, 1, "Baseline TFT", self.baseline_var, self._choose_baseline, column=3)
        ttk.Label(paths, text="Target").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(paths, textvariable=self.target_var).grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=3)

        actions = ttk.Frame(paths)
        actions.grid(row=2, column=3, columnspan=3, sticky="e", pady=3)
        ttk.Button(actions, text="New", command=self._new_scene).pack(side="left", padx=3)
        ttk.Button(actions, text="Import HMI", command=self._import_hmi_project).pack(side="left", padx=3)
        ttk.Button(actions, text="Roundtrip HMI", command=self._roundtrip_hmi_project).pack(side="left", padx=3)
        ttk.Button(actions, text="Load", command=self._load_scene_outline).pack(side="left", padx=3)
        ttk.Button(actions, text="Save As", command=self._save_scene_as).pack(side="left", padx=3)
        self.undo_button = ttk.Button(actions, text="Undo", command=self._undo_scene_edit, state="disabled")
        self.undo_button.pack(side="left", padx=3)
        self.redo_button = ttk.Button(actions, text="Redo", command=self._redo_scene_edit, state="disabled")
        self.redo_button.pack(side="left", padx=3)
        ttk.Button(actions, text="Check Scene", command=self._check_scene).pack(side="left", padx=3)
        ttk.Button(actions, text="Preview Bundle", command=lambda: self._generate(build_tft=False)).pack(side="left", padx=3)
        ttk.Button(actions, text="Export Bundle", command=self._export_bundle).pack(side="left", padx=3)
        ttk.Button(actions, text="Build TFT", command=lambda: self._generate(build_tft=True)).pack(side="left", padx=3)
        ttk.Button(actions, text="Open Folder", command=self._open_output_dir).pack(side="left", padx=3)
        self.root.bind_all("<Control-z>", self._shortcut_undo_scene)
        self.root.bind_all("<Control-y>", self._shortcut_redo_scene)

        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 12))

        left = ttk.Frame(body, padding=8)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="Objects", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.object_tree = ttk.Treeview(left, columns=("type", "support"), show="tree headings", selectmode="extended")
        self.object_tree.heading("#0", text="ID")
        self.object_tree.heading("type", text="Type")
        self.object_tree.heading("support", text="Support")
        self.object_tree.column("#0", width=150, stretch=True)
        self.object_tree.column("type", width=92, stretch=False)
        self.object_tree.column("support", width=94, stretch=False)
        self.object_tree.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self.object_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.object_tree.bind("<Delete>", self._shortcut_delete_widget)
        self.object_tree.bind("<Control-d>", self._shortcut_duplicate_widget)
        self.object_tree.bind("<Control-c>", self._shortcut_copy_widget)
        self.object_tree.bind("<Control-x>", self._shortcut_cut_widget)
        self.object_tree.bind("<Control-v>", self._shortcut_paste_widget)
        object_actions = ttk.Frame(left)
        object_actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(object_actions, text="Copy", command=self._copy_selected_widget).pack(side="left", padx=(0, 4))
        ttk.Button(object_actions, text="Cut", command=self._cut_selected_widget).pack(side="left", padx=4)
        ttk.Button(object_actions, text="Paste", command=self._paste_widget_clipboard).pack(side="left", padx=4)
        ttk.Button(object_actions, text="Duplicate", command=self._duplicate_selected_widget).pack(side="left", padx=(0, 4))
        ttk.Button(object_actions, text="Delete", command=self._delete_selected_widget).pack(side="left", padx=4)
        ttk.Button(object_actions, text="Up", command=lambda: self._move_selected_widget("up")).pack(side="left", padx=4)
        ttk.Button(object_actions, text="Down", command=lambda: self._move_selected_widget("down")).pack(side="left", padx=4)
        ttk.Button(object_actions, text="Front", command=lambda: self._move_selected_widget("front")).pack(side="left", padx=4)
        ttk.Button(object_actions, text="Back", command=lambda: self._move_selected_widget("back")).pack(side="left", padx=4)
        align_actions = ttk.Frame(left)
        align_actions.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        ttk.Label(align_actions, text="Align").pack(side="left", padx=(0, 4))
        ttk.Button(align_actions, text="Left", command=lambda: self._align_selected_widgets("left")).pack(side="left", padx=(0, 4))
        ttk.Button(align_actions, text="Top", command=lambda: self._align_selected_widgets("top")).pack(side="left", padx=4)
        ttk.Button(align_actions, text="H Center", command=lambda: self._align_selected_widgets("hcenter")).pack(side="left", padx=4)
        ttk.Button(align_actions, text="V Center", command=lambda: self._align_selected_widgets("vcenter")).pack(side="left", padx=4)
        ttk.Button(align_actions, text="Dist H", command=lambda: self._distribute_selected_widgets("horizontal")).pack(side="left", padx=4)
        ttk.Button(align_actions, text="Dist V", command=lambda: self._distribute_selected_widgets("vertical")).pack(side="left", padx=4)
        size_actions = ttk.Frame(left)
        size_actions.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        ttk.Label(size_actions, text="Size").pack(side="left", padx=(0, 4))
        ttk.Button(size_actions, text="Same W", command=lambda: self._match_size_selected_widgets("width")).pack(side="left", padx=(0, 4))
        ttk.Button(size_actions, text="Same H", command=lambda: self._match_size_selected_widgets("height")).pack(side="left", padx=4)
        ttk.Button(size_actions, text="Same Size", command=lambda: self._match_size_selected_widgets("both")).pack(side="left", padx=4)
        page_actions = ttk.Frame(left)
        page_actions.grid(row=5, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(page_actions, text="Add Page", command=self._add_page).pack(side="left", padx=(0, 4))
        ttk.Button(page_actions, text="Copy Page", command=self._duplicate_selected_page).pack(side="left", padx=4)
        ttk.Button(page_actions, text="Delete Page", command=self._delete_selected_page).pack(side="left", padx=4)
        ttk.Button(page_actions, text="Preview Page", command=self._preview_selected_page).pack(side="left", padx=4)
        body.add(left, weight=1)

        center = ttk.Frame(body, padding=8)
        center.columnconfigure(0, weight=1)
        center.rowconfigure(1, weight=1)
        center_actions = ttk.Frame(center)
        center_actions.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(center_actions, text="Open Preview", command=lambda: self._open_context_output("preview_png", "preview.png")).pack(side="left", padx=(0, 4))
        ttk.Button(center_actions, text="Open Annotated", command=lambda: self._open_context_output("annotated_preview_png", "preview.annotated.png")).pack(
            side="left",
            padx=4,
        )
        ttk.Button(center_actions, text="Open Context", command=lambda: self._open_context_output("agent_context_json", "agent_context.json")).pack(side="left", padx=4)
        ttk.Label(center_actions, text="Snap").pack(side="left", padx=(16, 4))
        ttk.Entry(center_actions, textvariable=self.snap_var, width=4).pack(side="left")
        self.preview_tabs = ttk.Notebook(center)
        self.preview_tabs.grid(row=1, column=0, sticky="nsew")
        preview_frame = ttk.Frame(self.preview_tabs, padding=8)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        self.preview_label = tk.Canvas(preview_frame, width=620, height=460, background="#f7f7f7", highlightthickness=1, highlightbackground="#b8b8b8")
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        self.preview_label.create_text(310, 230, text="Generate a preview bundle to render the scene.", fill="#555555")
        self.preview_label.bind("<Button-1>", self._on_preview_mouse_down)
        self.preview_label.bind("<B1-Motion>", self._on_preview_mouse_drag)
        self.preview_label.bind("<ButtonRelease-1>", self._on_preview_mouse_up)
        self.preview_label.bind("<KeyPress>", self._on_preview_key)
        self.preview_label.bind("<Delete>", self._shortcut_delete_widget)
        self.preview_label.bind("<Control-d>", self._shortcut_duplicate_widget)
        self.preview_label.bind("<Control-c>", self._shortcut_copy_widget)
        self.preview_label.bind("<Control-x>", self._shortcut_cut_widget)
        self.preview_label.bind("<Control-v>", self._shortcut_paste_widget)
        self.preview_tabs.add(preview_frame, text="Preview")
        annotated_frame = ttk.Frame(self.preview_tabs, padding=8)
        annotated_frame.columnconfigure(0, weight=1)
        annotated_frame.rowconfigure(0, weight=1)
        self.annotated_label = ttk.Label(annotated_frame, text="Annotated object boxes will appear here.", anchor="center")
        self.annotated_label.grid(row=0, column=0, sticky="nsew")
        self.preview_tabs.add(annotated_frame, text="Agent Overlay")
        body.add(center, weight=3)

        right = ttk.Frame(body, padding=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.side_tabs = ttk.Notebook(right)
        self.side_tabs.grid(row=0, column=0, sticky="nsew")
        self.inspector = self._text_tab(self.side_tabs, "Inspector")
        self.project_frame = self._project_tab(self.side_tabs)
        self.properties_frame = self._properties_tab(self.side_tabs)
        self.toolbox_frame = self._toolbox_tab(self.side_tabs)
        self.assets_frame = self._assets_tab(self.side_tabs)
        self.diagnostics_tree = self._diagnostics_tab(self.side_tabs)
        self.events_text = self._events_tab(self.side_tabs)
        self.agent_text = self._text_tab(self.side_tabs, "Agent")
        self.log = self._text_tab(self.side_tabs, "Log")
        body.add(right, weight=2)
        self._log("Ready. Load a scene or generate a preview bundle.")
        self._set_agent_text(None)

    def _text_tab(self, notebook: ttk.Notebook, title: str) -> tk.Text:
        frame = ttk.Frame(notebook, padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap="word", font=("Consolas", 9), height=12)
        text.grid(row=0, column=0, sticky="nsew")
        notebook.add(frame, text=title)
        return text

    def _diagnostics_tab(self, notebook: ttk.Notebook) -> ttk.Treeview:
        frame = ttk.Frame(notebook, padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=("severity", "code", "message"), show="headings")
        tree.heading("severity", text="Severity")
        tree.heading("code", text="Code")
        tree.heading("message", text="Message")
        tree.column("severity", width=76, stretch=False)
        tree.column("code", width=170, stretch=False)
        tree.column("message", width=320, stretch=True)
        tree.grid(row=0, column=0, sticky="nsew")
        notebook.add(frame, text="Diagnostics")
        return tree

    def _project_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(notebook, padding=8)
        frame.columnconfigure(1, weight=1)
        row = 0
        ttk.Label(frame, text="Project", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        for key, label in (
            ("name", "Name"),
            ("default_page", "Default Page"),
            ("width", "Width"),
            ("height", "Height"),
            ("background_color", "Background"),
        ):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Entry(frame, textvariable=self.project_vars[key]).grid(row=row, column=1, sticky="ew", pady=3)
            row += 1
        project_actions = ttk.Frame(frame)
        project_actions.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 12))
        ttk.Button(project_actions, text="Save Project", command=self._save_project_settings).pack(side="left", padx=(0, 4))
        ttk.Button(project_actions, text="Reload", command=self._reload_project_settings).pack(side="left", padx=4)
        row += 1

        ttk.Separator(frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        row += 1
        ttk.Label(frame, textvariable=self.page_target_var, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        ttk.Label(frame, text="Page ID").grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=self.page_vars["id"]).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1
        ttk.Label(frame, text="Layout JSON").grid(row=row, column=0, sticky="nw", pady=3)
        self.page_layout_text = tk.Text(frame, wrap="none", font=("Consolas", 9), height=5)
        self.page_layout_text.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1
        page_actions = ttk.Frame(frame)
        page_actions.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(page_actions, text="Save Page", command=self._save_page_settings).pack(side="left", padx=(0, 4))
        ttk.Button(page_actions, text="Reload Page", command=self._reload_page_settings).pack(side="left", padx=4)
        notebook.add(frame, text="Project")
        return frame

    def _properties_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(notebook, padding=8)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, textvariable=self.property_target_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        row = 1
        for key, label in (("id", "ID"), ("type", "Type"), ("x", "X"), ("y", "Y"), ("w", "W"), ("h", "H"), ("text", "Text"), ("value", "Value")):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            if key == "type":
                ttk.Combobox(frame, textvariable=self.property_vars[key], values=self.widget_type_options, state="readonly").grid(row=row, column=1, sticky="ew", pady=3)
            else:
                ttk.Entry(frame, textvariable=self.property_vars[key]).grid(row=row, column=1, sticky="ew", pady=3)
            row += 1
        for key, label in (("style", "Style JSON"), ("resources", "Resources JSON"), ("bindings", "Bindings JSON")):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="nw", pady=3)
            text = tk.Text(frame, wrap="none", font=("Consolas", 9), height=4)
            text.grid(row=row, column=1, sticky="ew", pady=3)
            self.property_json_texts[key] = text
            row += 1
        actions = ttk.Frame(frame)
        actions.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(actions, text="Save Properties", command=self._save_widget_properties).pack(side="left", padx=(0, 4))
        ttk.Button(actions, text="Reload", command=self._reload_widget_properties).pack(side="left", padx=4)
        ttk.Checkbutton(
            actions,
            text="Rewrite event refs on rename",
            variable=self.rewrite_widget_refs_var,
        ).pack(side="left", padx=(12, 4))
        notebook.add(frame, text="Properties")
        return frame

    def _toolbox_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(notebook, padding=8)
        frame.columnconfigure(1, weight=1)
        row = 0
        for key, label in (("page", "Page"), ("id", "ID"), ("type", "Type"), ("x", "X"), ("y", "Y"), ("w", "W"), ("h", "H"), ("text", "Text"), ("value", "Value")):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            if key == "type":
                ttk.Combobox(frame, textvariable=self.toolbox_vars[key], values=self.widget_type_options, state="readonly").grid(row=row, column=1, sticky="ew", pady=3)
            else:
                ttk.Entry(frame, textvariable=self.toolbox_vars[key]).grid(row=row, column=1, sticky="ew", pady=3)
            row += 1
        for key, label in (("style", "Style JSON"), ("resources", "Resources JSON"), ("bindings", "Bindings JSON")):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="nw", pady=3)
            text = tk.Text(frame, wrap="none", font=("Consolas", 9), height=3)
            text.grid(row=row, column=1, sticky="ew", pady=3)
            text.insert("end", "{}")
            self.toolbox_json_texts[key] = text
            row += 1
        actions = ttk.Frame(frame)
        actions.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(actions, text="Load Template", command=self._load_toolbox_template).pack(side="left", padx=(0, 4))
        ttk.Button(actions, text="Add Widget", command=self._add_widget_from_toolbox).pack(side="left", padx=(0, 4))
        ttk.Button(actions, text="Suggest ID", command=self._suggest_toolbox_id).pack(side="left", padx=4)
        ttk.Label(
            frame,
            text="Scene-only authoring. Build/upload remains a separate explicit operation.",
            wraplength=300,
            foreground="#555555",
        ).grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        notebook.add(frame, text="Toolbox")
        return frame

    def _assets_tab(self, notebook: ttk.Notebook) -> ttk.Frame:
        frame = ttk.Frame(notebook, padding=8)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        self.asset_tree = ttk.Treeview(frame, columns=("source", "normal"), show="tree headings", selectmode="browse", height=6)
        self.asset_tree.heading("#0", text="Key")
        self.asset_tree.heading("source", text="Source")
        self.asset_tree.heading("normal", text="Normal")
        self.asset_tree.column("#0", width=110, stretch=False)
        self.asset_tree.column("source", width=180, stretch=True)
        self.asset_tree.column("normal", width=180, stretch=True)
        self.asset_tree.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.asset_tree.bind("<<TreeviewSelect>>", self._on_asset_select)
        row = 1
        for key, label in (("key", "Key"), ("id", "Stored ID"), ("source", "Source"), ("normal", "Normal"), ("pressed", "Pressed"), ("disabled", "Disabled")):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Entry(frame, textvariable=self.asset_vars[key]).grid(row=row, column=1, sticky="ew", pady=3)
            if key in {"source", "normal", "pressed", "disabled"}:
                ttk.Button(frame, text="Browse", command=lambda item=key: self._choose_asset_file(item)).grid(row=row, column=2, sticky="ew", padx=(6, 0), pady=3)
            row += 1
        actions = ttk.Frame(frame)
        actions.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(actions, text="Add Asset", command=self._add_asset).pack(side="left", padx=(0, 4))
        ttk.Button(actions, text="Update Asset", command=self._update_asset).pack(side="left", padx=4)
        ttk.Button(actions, text="Delete Asset", command=self._delete_asset).pack(side="left", padx=4)
        ttk.Button(actions, text="Reload", command=self._refresh_assets_from_scene).pack(side="left", padx=4)
        notebook.add(frame, text="Assets")
        return frame

    def _events_tab(self, notebook: ttk.Notebook) -> tk.Text:
        frame = ttk.Frame(notebook, padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        toolbar = ttk.Frame(frame)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Target").grid(row=0, column=0, sticky="w")
        ttk.Label(toolbar, textvariable=self.event_target_var).grid(row=0, column=1, sticky="w", padx=(6, 10))
        ttk.Label(toolbar, text="Event").grid(row=0, column=2, sticky="e")
        combo = ttk.Combobox(toolbar, textvariable=self.event_name_var, values=EVENT_NAMES, width=10, state="readonly")
        combo.grid(row=0, column=3, sticky="e", padx=(6, 0))
        combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_event_editor())
        actions = ttk.Frame(frame)
        actions.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        ttk.Button(actions, text="Reload", command=self._refresh_event_editor).pack(side="left", padx=(0, 4))
        ttk.Button(actions, text="Save Event", command=self._save_selected_event).pack(side="left", padx=4)
        ttk.Button(actions, text="Clear Event", command=self._clear_selected_event).pack(side="left", padx=4)
        ttk.Button(actions, text="Save+Simulate", command=self._simulate_selected_event).pack(side="left", padx=4)
        ttk.Combobox(
            actions,
            textvariable=self.event_snippet_var,
            values=[item["label"] for item in self.event_snippets],
            state="readonly",
            width=18,
        ).pack(side="left", padx=(12, 4))
        ttk.Button(actions, text="Insert Snippet", command=self._insert_event_snippet).pack(side="left", padx=4)
        ttk.Button(actions, text="Line Up", command=self._move_event_line_up).pack(side="left", padx=4)
        ttk.Button(actions, text="Line Down", command=self._move_event_line_down).pack(side="left", padx=4)
        ttk.Button(actions, text="Delete Line", command=self._delete_event_line).pack(side="left", padx=4)
        text = tk.Text(frame, wrap="none", font=("Consolas", 9), height=12)
        text.grid(row=2, column=0, sticky="nsew")
        notebook.add(frame, text="Events")
        return text

    def _path_row(self, parent: ttk.Frame, row: int, label: str, var: tk.StringVar, command, *, column: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=column + 1, sticky="ew", padx=(8, 8), pady=3)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=column + 2, sticky="ew", pady=3)

    def _choose_scene(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose scene JSON/YAML",
            initialdir=str(self.repo_root / "examples" if self.repo_root.exists() else Path.home()),
            filetypes=[("Scene files", "*.json *.yaml *.yml"), ("All files", "*.*")],
        )
        if path:
            self.scene_var.set(path)
            self._load_scene_outline()

    def _new_scene(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Create scene JSON/YAML",
            initialdir=str(self.repo_root / "examples" if self.repo_root.exists() else Path.home()),
            defaultextension=".json",
            filetypes=[("Scene JSON", "*.json"), ("Scene YAML", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not path:
            return
        file_path = Path(path).expanduser()
        overwrite = file_path.exists() and messagebox.askyesno(APP_TITLE, f"Overwrite existing scene?\n{file_path}")
        if file_path.exists() and not overwrite:
            return
        try:
            result = create_scene_document(file_path, project_name=file_path.stem, overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR creating scene: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.scene_var.set(result["scene_path"])
        self._log(f"Created scene: {result['scene_path']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _save_scene_as(self) -> None:
        source = Path(self.scene_var.get()).expanduser()
        if not source.exists():
            messagebox.showinfo(APP_TITLE, "Load a scene first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save scene as",
            initialdir=str(source.parent),
            initialfile=source.name,
            defaultextension=source.suffix or ".json",
            filetypes=[("Scene JSON", "*.json"), ("Scene YAML", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not path:
            return
        destination = Path(path).expanduser()
        overwrite = destination.exists() and messagebox.askyesno(APP_TITLE, f"Overwrite existing scene?\n{destination}")
        if destination.exists() and not overwrite:
            return
        try:
            result = save_scene_document_as(source, destination, overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR saving scene as: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.scene_var.set(result["scene_path"])
        self._log(f"Saved scene as: {result['scene_path']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _import_hmi_project(self) -> None:
        hmi_path = filedialog.askopenfilename(
            title="Import official HMI",
            initialdir=str(self.repo_root if self.repo_root.exists() else Path.home()),
            filetypes=[("HMI files", "*.HMI *.hmi"), ("All files", "*.*")],
        )
        if not hmi_path:
            return
        base_out = Path(self.out_var.get()).expanduser()
        default_out = base_out / f"imported_{Path(hmi_path).stem}"
        out_dir = filedialog.askdirectory(
            title="Choose import output directory",
            initialdir=str(default_out.parent if default_out.parent.exists() else base_out),
        )
        if not out_dir:
            return
        output = Path(out_dir).expanduser()
        overwrite = output.exists() and any(output.iterdir()) and messagebox.askyesno(APP_TITLE, f"Overwrite import outputs in?\n{output}")
        try:
            result = import_hmi_project(hmi_path, output, target=self.target_var.get(), overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001 - GUI should surface import failures.
            self._log(f"ERROR importing HMI: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.scene_var.set(result["scene_path"])
        self.out_var.set(str(output))
        self._log(f"Imported HMI: {result['scene_path']}")
        self._log(f"Import report: {result['import_report']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _roundtrip_hmi_project(self) -> None:
        hmi_path = filedialog.askopenfilename(
            title="Roundtrip-check official HMI",
            initialdir=str(self.repo_root if self.repo_root.exists() else Path.home()),
            filetypes=[("HMI files", "*.HMI *.hmi"), ("All files", "*.*")],
        )
        if not hmi_path:
            return
        base_out = Path(self.out_var.get()).expanduser()
        default_out = base_out / f"roundtrip_{Path(hmi_path).stem}"
        out_dir = filedialog.askdirectory(
            title="Choose roundtrip output directory",
            initialdir=str(default_out.parent if default_out.parent.exists() else base_out),
        )
        if not out_dir:
            return
        output = Path(out_dir).expanduser()
        overwrite = output.exists() and any(output.iterdir()) and messagebox.askyesno(APP_TITLE, f"Overwrite roundtrip outputs in?\n{output}")
        self._log(f"Roundtrip-checking HMI: {hmi_path}")
        worker = threading.Thread(
            target=self._worker_roundtrip_hmi,
            args=(Path(hmi_path), output, self.target_var.get(), overwrite),
            daemon=True,
        )
        worker.start()

    def _reload_project_settings(self) -> None:
        try:
            scene = load_scene(self.scene_var.get())
        except Exception as exc:  # noqa: BLE001 - GUI should surface parse failures.
            self._log(f"ERROR reloading project settings: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._set_project_settings_from_scene(scene)
        self._log("Reloaded project settings")

    def _save_project_settings(self) -> None:
        try:
            result = update_scene_project(
                self.scene_var.get(),
                name=self.project_vars["name"].get().strip() or None,
                default_page=self.project_vars["default_page"].get().strip() or None,
                width=_optional_int_var(self.project_vars["width"]),
                height=_optional_int_var(self.project_vars["height"]),
                background_color=_optional_int_var(self.project_vars["background_color"]),
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR saving project settings: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(
            f"Saved project: {result['project'].get('name')} "
            f"{result['canvas'].get('width')}x{result['canvas'].get('height')} "
            f"default={result['project'].get('default_page')}"
        )
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _reload_page_settings(self) -> None:
        payload = self._selected_page_for_action()
        if not payload:
            return
        self._set_page_settings(payload)
        self._log(f"Reloaded page settings: {payload.get('id')}")

    def _save_page_settings(self) -> None:
        payload = self._selected_page_for_action()
        if not payload:
            return
        try:
            layout = _json_text_map(self.page_layout_text, "page layout") if self.page_layout_text is not None else None
            result = update_scene_page(
                self.scene_var.get(),
                page_id=str(payload["id"]),
                new_id=self.page_vars["id"].get().strip() or None,
                layout=layout,
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR saving page settings: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Saved page: {payload['id']} -> {result['page']['id']}; default={result.get('default_page')}")
        for warning in result.get("warnings", []):
            self._log(f"WARNING {warning.get('code')}: {warning.get('owner')} {warning.get('line')}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Choose output directory", initialdir=str(self.repo_root if self.repo_root.exists() else Path.home()))
        if path:
            self.out_var.set(path)

    def _choose_seed(self) -> None:
        path = filedialog.askopenfilename(title="Choose seed HMI", filetypes=[("HMI files", "*.HMI *.hmi"), ("All files", "*.*")])
        if path:
            self.seed_var.set(path)

    def _choose_baseline(self) -> None:
        path = filedialog.askopenfilename(title="Choose baseline TFT", filetypes=[("TFT files", "*.tft"), ("All files", "*.*")])
        if path:
            self.baseline_var.set(path)

    def _track_scene_history(self, *, label: str = "scene edit") -> None:
        snapshot = self._read_scene_snapshot()
        if snapshot is None:
            return
        path = snapshot["path"]
        text = snapshot["text"]
        if self._scene_history_suspended:
            self._scene_history_path = path
            self._scene_history_snapshot = text
            self._update_undo_redo_buttons()
            return
        if self._scene_history_path != path:
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._scene_history_path = path
            self._scene_history_snapshot = text
            self._update_undo_redo_buttons()
            return
        if self._scene_history_snapshot is not None and self._scene_history_snapshot != text:
            self.undo_stack.append(
                {
                    "path": path,
                    "before": self._scene_history_snapshot,
                    "after": text,
                    "label": label,
                }
            )
            self.undo_stack = self.undo_stack[-50:]
            self.redo_stack.clear()
            self._log(f"Undo point captured: {label}")
        self._scene_history_snapshot = text
        self._update_undo_redo_buttons()

    def _read_scene_snapshot(self) -> dict[str, str] | None:
        raw_path = self.scene_var.get().strip()
        if not raw_path:
            return None
        path = Path(raw_path).expanduser()
        if not path.exists() or not path.is_file():
            return None
        try:
            return {"path": str(path.resolve()), "text": path.read_text(encoding="utf-8")}
        except OSError as exc:
            self._log(f"WARNING unable to snapshot scene: {exc}")
            return None

    def _undo_scene_edit(self) -> None:
        if not self.undo_stack:
            self._update_undo_redo_buttons()
            return
        entry = self.undo_stack.pop()
        self.redo_stack.append(entry)
        self._restore_scene_history_entry(entry, text_key="before", label="Undo")

    def _redo_scene_edit(self) -> None:
        if not self.redo_stack:
            self._update_undo_redo_buttons()
            return
        entry = self.redo_stack.pop()
        self.undo_stack.append(entry)
        self._restore_scene_history_entry(entry, text_key="after", label="Redo")

    def _restore_scene_history_entry(self, entry: dict[str, str], *, text_key: str, label: str) -> None:
        path = Path(entry["path"])
        self._scene_history_suspended = True
        try:
            path.write_text(entry[text_key], encoding="utf-8")
            self.scene_var.set(str(path))
            self._scene_history_path = str(path.resolve())
            self._scene_history_snapshot = entry[text_key]
            self._log(f"{label}: {entry.get('label', 'scene edit')}")
            self._load_scene_outline(silent=True)
            self._generate(build_tft=False)
        except Exception as exc:  # noqa: BLE001 - GUI should surface restore failures.
            self._log(f"ERROR {label.lower()} scene edit: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
        finally:
            self._scene_history_suspended = False
            self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self) -> None:
        if self.undo_button is not None:
            self.undo_button.configure(state="normal" if self.undo_stack else "disabled")
        if self.redo_button is not None:
            self.redo_button.configure(state="normal" if self.redo_stack else "disabled")

    def _shortcut_undo_scene(self, event: tk.Event) -> str | None:
        if _is_text_input_widget(event.widget):
            return None
        self._undo_scene_edit()
        return "break"

    def _shortcut_redo_scene(self, event: tk.Event) -> str | None:
        if _is_text_input_widget(event.widget):
            return None
        self._redo_scene_edit()
        return "break"

    def _load_scene_outline(self, *, silent: bool = False) -> None:
        scene_path = Path(self.scene_var.get()).expanduser()
        if not scene_path.exists():
            if not silent:
                messagebox.showerror(APP_TITLE, f"Scene does not exist:\n{scene_path}")
            return
        try:
            scene = load_scene(scene_path)
        except Exception as exc:  # noqa: BLE001 - GUI should surface parse failures.
            if not silent:
                messagebox.showerror(APP_TITLE, str(exc))
            self._log(f"ERROR loading scene: {exc}")
            return
        self.tree_payloads.clear()
        self.object_tree.delete(*self.object_tree.get_children())
        self._set_project_settings_from_scene(scene)
        for page in scene.pages:
            page_id = f"page:{page.id}"
            self.object_tree.insert("", "end", iid=page_id, text=page.id, values=("page", ""))
            self.tree_payloads[page_id] = {
                "kind": "page",
                "id": page.id,
                "layout": dict(page.layout),
                "widgets": len(page.widgets),
                "events": dict(page.events),
            }
            for widget_index, widget in enumerate(page.widgets):
                capability = get_widget_capability(widget.type)
                item_id = f"widget:{page.id}:{widget_index}:{widget.id}"
                self.object_tree.insert(
                    page_id,
                    "end",
                    iid=item_id,
                    text=widget.id,
                    values=(widget.type, capability.get("support", "unknown")),
                )
                self.tree_payloads[item_id] = {
                    "kind": "widget",
                    "page": page.id,
                    "id": widget.id,
                    "type": widget.type,
                    "bbox": [widget.x, widget.y, widget.w, widget.h],
                    "text": widget.text,
                    "value": widget.value,
                    "events": {key: list(lines) for key, lines in widget.events.items()},
                    "capability": capability,
                }
            self.object_tree.item(page_id, open=True)
        self._set_inspector({"scene": str(scene_path), "canvas": scene.canvas, "pages": len(scene.pages)})
        self._populate_assets(list_scene_assets(scene_path).get("assets", []))
        self._track_scene_history(label="scene edit")
        self._log(f"Loaded scene outline: {scene_path}")

    def _generate(self, *, build_tft: bool) -> None:
        scene_path = Path(self.scene_var.get()).expanduser()
        out_dir = Path(self.out_var.get()).expanduser()
        target = self.target_var.get()
        seed = Path(self.seed_var.get()).expanduser()
        baseline = Path(self.baseline_var.get()).expanduser()
        if not scene_path.exists():
            messagebox.showerror(APP_TITLE, f"Scene does not exist:\n{scene_path}")
            return
        self._track_scene_history(label="scene edit")
        page_id = self._selected_preview_page_id()
        if build_tft and (not seed.exists() or not baseline.exists()):
            messagebox.showerror(APP_TITLE, "Seed HMI or baseline TFT is missing.")
            return
        verb = "Building TFT and agent bundle" if build_tft else "Generating agent preview bundle"
        page_suffix = f" page={page_id}" if page_id else ""
        self._log(f"{verb}: {scene_path}{page_suffix}")
        worker = threading.Thread(
            target=self._worker_generate,
            args=(scene_path, out_dir, target, build_tft, seed, baseline, page_id),
            daemon=True,
        )
        worker.start()

    def _export_bundle(self) -> None:
        scene_path = Path(self.scene_var.get()).expanduser()
        out_dir = Path(self.out_var.get()).expanduser()
        target = self.target_var.get()
        seed = Path(self.seed_var.get()).expanduser() if self.seed_var.get() else None
        baseline = Path(self.baseline_var.get()).expanduser() if self.baseline_var.get() else None
        if not scene_path.exists():
            messagebox.showerror(APP_TITLE, f"Scene does not exist:\n{scene_path}")
            return
        seed_arg = seed if seed and seed.exists() else None
        baseline_arg = baseline if baseline and baseline.exists() else None
        self._log(f"Exporting compile-style bundle: {scene_path}")
        worker = threading.Thread(
            target=self._worker_export_bundle,
            args=(scene_path, out_dir, target, seed_arg, baseline_arg),
            daemon=True,
        )
        worker.start()

    def _check_scene(self) -> None:
        scene_path = Path(self.scene_var.get()).expanduser()
        out_dir = Path(self.out_var.get()).expanduser()
        target = self.target_var.get()
        if not scene_path.exists():
            messagebox.showerror(APP_TITLE, f"Scene does not exist:\n{scene_path}")
            return
        self._log(f"Checking scene: {scene_path}")
        worker = threading.Thread(
            target=self._worker_check_scene,
            args=(scene_path, out_dir, target),
            daemon=True,
        )
        worker.start()

    def _worker_generate(
        self,
        scene_path: Path,
        out_dir: Path,
        target: str,
        build_tft: bool,
        seed: Path,
        baseline: Path,
        page_id: str | None,
    ) -> None:
        try:
            context = generate_agent_preview(scene_path, out_dir, target=target, page_id=page_id)
            build_result = None
            if build_tft:
                build_result = build_scene_artifacts(scene_path, seed, out_dir, baseline_tft=baseline)
            self.queue.put(("done", {"context": context, "build": build_result}))
        except Exception as exc:  # noqa: BLE001 - GUI needs to surface any failure.
            self.queue.put(("error", exc))

    def _worker_check_scene(self, scene_path: Path, out_dir: Path, target: str) -> None:
        try:
            report = check_scene_project(scene_path, out_dir=out_dir, target=target, simulate_events=True)
            self.queue.put(("check_done", report))
        except Exception as exc:  # noqa: BLE001 - GUI needs to surface any failure.
            self.queue.put(("error", exc))

    def _worker_export_bundle(self, scene_path: Path, out_dir: Path, target: str, seed: Path | None, baseline: Path | None) -> None:
        try:
            report = export_scene_bundle(scene_path, out_dir, seed_hmi=seed, baseline_tft=baseline, target=target)
            self.queue.put(("export_done", report))
        except Exception as exc:  # noqa: BLE001 - GUI needs to surface any failure.
            self.queue.put(("error", exc))

    def _worker_roundtrip_hmi(self, hmi_path: Path, out_dir: Path, target: str, overwrite: bool) -> None:
        try:
            report = check_hmi_roundtrip(hmi_path, out_dir, target=target, overwrite=overwrite)
            self.queue.put(("roundtrip_done", report))
        except Exception as exc:  # noqa: BLE001 - GUI needs to surface any failure.
            self.queue.put(("error", exc))

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "done":
                    self.last_context = payload["context"]
                    self._populate_from_context(self.last_context)
                    self._load_preview(Path(self.last_context["outputs"]["preview_png"]), self.preview_label, "preview")
                    self._load_preview(Path(self.last_context["outputs"]["annotated_preview_png"]), self.annotated_label, "annotated")
                    self._set_agent_text(self.last_context)
                    self._update_diagnostics(self.last_context.get("diagnostics", []))
                    diagnostics = self.last_context.get("diagnostics", [])
                    self._log(f"Agent bundle: {self.last_context['outputs']['agent_context_json']}")
                    self._log(f"Widgets: {len(self.last_context.get('widgets', []))}; diagnostics: {len(diagnostics)}")
                    if payload.get("build"):
                        result = payload["build"]
                        self._log(f"Built TFT: {result.get('output_tft')}")
                        checksum = result.get("tft_checksum") or {}
                        self._log(f"Checksum valid: {checksum.get('valid')} {checksum.get('stored_hex', '')}")
                elif kind == "check_done":
                    report = payload
                    summary = report.get("summary", {})
                    self._update_diagnostics(report.get("diagnostics", []))
                    self._set_inspector(
                        {
                            "scene_check": {
                                "summary": summary,
                                "outputs": report.get("outputs", {}),
                                "safe_to_flash": report.get("safe_to_flash"),
                                "not_claimed": report.get("not_claimed"),
                            }
                        }
                    )
                    self._log(
                        "Scene check: "
                        f"ok={summary.get('ok')} "
                        f"direct_tft={summary.get('direct_tft_ready')} "
                        f"widgets={summary.get('widget_count')} "
                        f"events={summary.get('event_slot_count')} "
                        f"errors={summary.get('error_count')} "
                        f"warnings={summary.get('warning_count')}"
                    )
                    output = report.get("outputs", {}).get("scene_check_report_json")
                    if output:
                        self._log(f"Scene check report: {output}")
                elif kind == "export_done":
                    report = payload
                    context_path = report.get("outputs", {}).get("agent_context_json")
                    if context_path and Path(context_path).exists():
                        self.last_context = json.loads(Path(context_path).read_text(encoding="utf-8"))
                        self._populate_from_context(self.last_context)
                        self._load_preview(Path(self.last_context["outputs"]["preview_png"]), self.preview_label, "preview")
                        self._load_preview(Path(self.last_context["outputs"]["annotated_preview_png"]), self.annotated_label, "annotated")
                        self._set_agent_text(self.last_context)
                        self._update_diagnostics(self.last_context.get("diagnostics", []))
                    self._log(f"Export report: {report['outputs']['export_report_json']}")
                    self._log(
                        "Export summary: "
                        f"ok={report.get('summary', {}).get('ok')} "
                        f"hmi={report.get('summary', {}).get('hmi_built')} "
                        f"tft={report.get('summary', {}).get('tft_built')}"
                    )
                elif kind == "roundtrip_done":
                    report = payload
                    outputs = report.get("outputs", {})
                    scene_path = outputs.get("scene_imported_json")
                    context_path = outputs.get("agent_context_json")
                    if scene_path:
                        self.scene_var.set(scene_path)
                    report_json = outputs.get("roundtrip_report_json")
                    if report_json:
                        self.out_var.set(str(Path(report_json).parent))
                    if context_path and Path(context_path).exists():
                        self.last_context = json.loads(Path(context_path).read_text(encoding="utf-8"))
                        self._populate_from_context(self.last_context)
                        self._load_preview(Path(self.last_context["outputs"]["preview_png"]), self.preview_label, "preview")
                        self._load_preview(Path(self.last_context["outputs"]["annotated_preview_png"]), self.annotated_label, "annotated")
                        self._set_agent_text(self.last_context)
                        self._update_diagnostics(self.last_context.get("diagnostics", []))
                    self._set_inspector(
                        {
                            "hmi_roundtrip": {
                                "summary": report.get("summary", {}),
                                "outputs": outputs,
                                "blocking_byte_perfect": report.get("blocking_byte_perfect", []),
                                "safe_to_flash": report.get("safe_to_flash"),
                                "not_claimed": report.get("not_claimed"),
                            }
                        }
                    )
                    summary = report.get("summary", {})
                    self._log(f"Roundtrip report: {outputs.get('roundtrip_report_json')}")
                    self._log(
                        "Roundtrip summary: "
                        f"byte_perfect={summary.get('byte_perfect')} "
                        f"objects={summary.get('objects_source')}->{summary.get('objects_regenerated')} "
                        f"blocking={summary.get('blocking_issues')} "
                        f"safe_to_flash={summary.get('safe_to_flash')}"
                    )
                elif kind == "error":
                    self._log(f"ERROR: {payload}")
                    messagebox.showerror(APP_TITLE, str(payload))
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queue)

    def _populate_from_context(self, context: dict[str, Any]) -> None:
        self.tree_payloads.clear()
        self.object_tree.delete(*self.object_tree.get_children())
        pages: dict[str, list[dict[str, Any]]] = {}
        page_meta = {str(item.get("id")): item for item in context.get("pages", []) if item.get("id")}
        page_events: dict[str, dict[str, list[str]]] = {}
        for event in context.get("events", []):
            if event.get("kind") == "page" and event.get("lines"):
                page_events.setdefault(event["page"], {})[event["event"]] = list(event["lines"])
        for widget in context.get("widgets", []):
            pages.setdefault(widget["page"], []).append(widget)
        for page in [str(item.get("id")) for item in context.get("pages", []) if item.get("id")] or list(pages):
            widgets = pages.get(page, [])
            page_id = f"page:{page}"
            self.object_tree.insert("", "end", iid=page_id, text=page, values=("page", ""))
            self.tree_payloads[page_id] = {
                "kind": "page",
                "id": page,
                "layout": dict(page_meta.get(page, {}).get("layout") or {"type": "absolute"}),
                "widgets": len(widgets),
                "events": page_events.get(page, {}),
            }
            for widget in widgets:
                item_id = f"widget:{page}:{widget['z_index']}:{widget['id']}"
                capability = widget.get("capability", {})
                self.object_tree.insert(
                    page_id,
                    "end",
                    iid=item_id,
                    text=widget["id"],
                    values=(widget["type"], capability.get("support", "unknown")),
                )
                self.tree_payloads[item_id] = {**widget, "kind": "widget"}
            self.object_tree.item(page_id, open=True)
        self._set_project_settings_from_context(context)
        self._set_inspector(
            {
                "target": context.get("input", {}).get("target"),
                "project": context.get("project"),
                "canvas": context.get("canvas"),
                "pages": len(context.get("pages", [])),
                "assets": len(context.get("assets", [])),
                "widgets": len(context.get("widgets", [])),
                "diagnostics": len(context.get("diagnostics", [])),
                "outputs": context.get("outputs"),
            }
        )
        self._populate_assets(context.get("assets", []))

    def _set_project_settings_from_scene(self, scene) -> None:
        self.project_vars["name"].set(str(scene.project.get("name") or ""))
        self.project_vars["default_page"].set(str(scene.project.get("default_page") or ""))
        self.project_vars["width"].set(str(scene.canvas.get("width") or ""))
        self.project_vars["height"].set(str(scene.canvas.get("height") or ""))
        self.project_vars["background_color"].set(str(scene.canvas.get("background_color", "")))

    def _set_project_settings_from_context(self, context: dict[str, Any]) -> None:
        project = context.get("project") or {}
        canvas = context.get("canvas") or {}
        self.project_vars["name"].set(str(project.get("name") or ""))
        self.project_vars["default_page"].set(str(project.get("default_page") or ""))
        self.project_vars["width"].set(str(canvas.get("width") or ""))
        self.project_vars["height"].set(str(canvas.get("height") or ""))
        self.project_vars["background_color"].set(str(canvas.get("background_color", "")))

    def _set_page_settings(self, payload: dict[str, Any]) -> None:
        self.selected_page_payload = payload
        page_id = str(payload.get("id") or "")
        self.page_target_var.set(f"Page {page_id}" if page_id else "Select a page")
        self.page_vars["id"].set(page_id)
        if self.page_layout_text is not None:
            layout = payload.get("layout") or {"type": "absolute"}
            self._replace_text(self.page_layout_text, json.dumps(layout, ensure_ascii=False, indent=2))

    def _populate_assets(self, assets: list[dict[str, Any]]) -> None:
        self.asset_payloads.clear()
        self.asset_tree.delete(*self.asset_tree.get_children())
        for asset in assets:
            key = str(asset.get("key") or asset.get("id") or "")
            if not key:
                continue
            item_id = f"asset:{key}"
            self.asset_tree.insert(
                "",
                "end",
                iid=item_id,
                text=key,
                values=(asset.get("source") or "", asset.get("normal") or ""),
            )
            self.asset_payloads[item_id] = asset

    def _refresh_assets_from_scene(self) -> None:
        try:
            assets = list_scene_assets(self.scene_var.get()).get("assets", [])
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR loading assets: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._populate_assets(assets)
        self._log(f"Loaded assets: {len(assets)}")

    def _on_asset_select(self, _event: tk.Event) -> None:
        selection = self.asset_tree.selection()
        if not selection:
            return
        payload = self.asset_payloads.get(selection[0])
        if not payload:
            return
        for key in ("key", "id", "source", "normal", "pressed", "disabled"):
            self.asset_vars[key].set("" if payload.get(key) is None else str(payload.get(key)))
        self._set_inspector({"kind": "asset", **payload})

    def _choose_asset_file(self, key: str) -> None:
        path = filedialog.askopenfilename(
            title=f"Choose {key} asset image",
            initialdir=str(Path(self.scene_var.get()).expanduser().parent if self.scene_var.get() else Path.home()),
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
        )
        if path:
            self.asset_vars[key].set(path)

    def _add_asset(self) -> None:
        asset_id = self.asset_vars["key"].get().strip()
        if not asset_id:
            messagebox.showinfo(APP_TITLE, "Asset key is required.")
            return
        try:
            result = add_scene_asset(self.scene_var.get(), asset_id=asset_id, asset=_asset_from_vars(self.asset_vars))
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR adding asset {asset_id}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Added asset: {result['asset']['key']}")
        self._refresh_assets_from_scene()
        self._generate(build_tft=False)

    def _update_asset(self) -> None:
        asset_id = self.asset_vars["key"].get().strip()
        if not asset_id:
            messagebox.showinfo(APP_TITLE, "Asset key is required.")
            return
        try:
            result = update_scene_asset(self.scene_var.get(), asset_id=asset_id, updates=_asset_from_vars(self.asset_vars))
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR updating asset {asset_id}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Updated asset: {result['asset']['key']}")
        self._refresh_assets_from_scene()
        self._generate(build_tft=False)

    def _delete_asset(self) -> None:
        asset_id = self.asset_vars["key"].get().strip()
        if not asset_id:
            messagebox.showinfo(APP_TITLE, "Asset key is required.")
            return
        if not messagebox.askyesno(APP_TITLE, f"Delete asset {asset_id}?"):
            return
        try:
            result = delete_scene_asset(self.scene_var.get(), asset_id=asset_id)
        except Exception as exc:  # noqa: BLE001 - GUI should surface referenced-asset failures.
            if not messagebox.askyesno(APP_TITLE, f"{exc}\n\nForce delete asset {asset_id}?"):
                self._log(f"Asset delete blocked: {exc}")
                return
            try:
                result = delete_scene_asset(self.scene_var.get(), asset_id=asset_id, force=True)
            except Exception as force_exc:  # noqa: BLE001 - GUI should surface edit failures.
                self._log(f"ERROR deleting asset {asset_id}: {force_exc}")
                messagebox.showerror(APP_TITLE, str(force_exc))
                return
        self._log(f"Deleted asset: {result['deleted_asset']['key']}; references={len(result.get('references', []))}")
        for var in self.asset_vars.values():
            var.set("")
        self._refresh_assets_from_scene()
        self._generate(build_tft=False)

    def _update_diagnostics(self, diagnostics: list[dict[str, Any]]) -> None:
        self.diagnostics_tree.delete(*self.diagnostics_tree.get_children())
        for index, diagnostic in enumerate(diagnostics):
            self.diagnostics_tree.insert(
                "",
                "end",
                iid=f"diag:{index}",
                values=(diagnostic.get("severity", ""), diagnostic.get("code", ""), diagnostic.get("message", "")),
            )

    def _refresh_preview_overlays(self) -> None:
        if not isinstance(self.preview_label, tk.Canvas):
            return
        for item_id in self.preview_overlay_ids:
            self.preview_label.delete(item_id)
        self.preview_overlay_ids = []
        context = self.last_context
        if not context or not self.preview_display:
            return
        selected_keys = {
            (str(item.get("page")), str(item.get("id")))
            for item in self.selected_widget_payloads
            if item.get("kind") == "widget"
        }
        if self.selected_widget_payload and self.selected_widget_payload.get("kind") == "widget":
            selected_keys.add((str(self.selected_widget_payload.get("page")), str(self.selected_widget_payload.get("id"))))
        page_id = context.get("input", {}).get("page_id")
        for widget in context.get("widgets", []):
            if page_id and widget.get("page") != page_id:
                continue
            bbox = widget.get("bbox") or []
            if len(bbox) != 4 or int(bbox[2]) <= 0 or int(bbox[3]) <= 0:
                continue
            x0, y0, x1, y1 = self._scene_bbox_to_display([int(value) for value in bbox])
            is_selected = (str(widget.get("page")), str(widget.get("id"))) in selected_keys
            outline = "#d92d20" if is_selected else "#2563eb"
            width = 2 if is_selected else 1
            self.preview_overlay_ids.append(
                self.preview_label.create_rectangle(x0, y0, x1, y1, outline=outline, width=width, tags=("overlay",))
            )
            if is_selected:
                self.preview_overlay_ids.append(
                    self.preview_label.create_rectangle(
                        x1 - 6,
                        y1 - 6,
                        x1 + 4,
                        y1 + 4,
                        outline="#d92d20",
                        fill="#ffffff",
                        tags=("overlay",),
                    )
                )
        if self.preview_temp_rect is not None:
            self.preview_label.tag_raise(self.preview_temp_rect)

    def _on_preview_mouse_down(self, event: tk.Event) -> None:
        if not isinstance(self.preview_label, tk.Canvas):
            return
        self.preview_label.focus_set()
        hit = self._preview_hit_test(int(event.x), int(event.y))
        if hit is None:
            return
        self._select_widget_payload(hit)
        scene_x, scene_y = self._display_point_to_scene(int(event.x), int(event.y))
        bbox = [int(value) for value in hit.get("bbox") or [0, 0, 1, 1]]
        mode = "resize" if self._near_resize_handle(scene_x, scene_y, bbox) else "move"
        self.preview_drag = {
            "mode": mode,
            "page": hit["page"],
            "widget": hit["id"],
            "start": [scene_x, scene_y],
            "from": bbox,
        }
        self._draw_preview_temp_rect(bbox)

    def _on_preview_mouse_drag(self, event: tk.Event) -> None:
        drag = self.preview_drag
        if drag is None:
            return
        scene_x, scene_y = self._display_point_to_scene(int(event.x), int(event.y))
        bbox = self._dragged_bbox(drag, scene_x, scene_y)
        self._draw_preview_temp_rect(bbox)

    def _on_preview_mouse_up(self, event: tk.Event) -> None:
        drag = self.preview_drag
        self.preview_drag = None
        if drag is None:
            return
        scene_x, scene_y = self._display_point_to_scene(int(event.x), int(event.y))
        bbox = self._dragged_bbox(drag, scene_x, scene_y)
        if self.preview_temp_rect is not None:
            self.preview_label.delete(self.preview_temp_rect)
            self.preview_temp_rect = None
        try:
            if drag["mode"] == "resize":
                result = design_resize_widget(
                    self.scene_var.get(),
                    self.out_var.get(),
                    page_id=str(drag["page"]),
                    widget_id=str(drag["widget"]),
                    w=bbox[2],
                    h=bbox[3],
                    snap=self._design_snap(),
                    source="gui-canvas-resize",
                )
            else:
                result = design_move_widget(
                    self.scene_var.get(),
                    self.out_var.get(),
                    page_id=str(drag["page"]),
                    widget_id=str(drag["widget"]),
                    x=bbox[0],
                    y=bbox[1],
                    snap=self._design_snap(),
                    source="gui-canvas-drag",
                )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR applying canvas edit: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            self._refresh_preview_overlays()
            return
        self._log(f"Canvas {result['op']['op']}: {result['page']}.{result['widget']['id']} -> {result['op']['to']}")
        self._log(f"Agent patch: {result['outputs']['agent_patch_json']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _on_preview_key(self, event: tk.Event) -> str | None:
        payload = self.selected_widget_payload
        if not payload or payload.get("kind") != "widget":
            return None
        deltas = {
            "Left": (-1, 0),
            "Right": (1, 0),
            "Up": (0, -1),
            "Down": (0, 1),
        }
        if event.keysym not in deltas:
            return None
        step = 10 if int(event.state) & 0x0001 else 1
        dx, dy = deltas[event.keysym]
        try:
            result = design_move_widget(
                self.scene_var.get(),
                self.out_var.get(),
                page_id=str(payload["page"]),
                widget_id=str(payload["id"]),
                dx=dx * step,
                dy=dy * step,
                source="gui-keyboard-nudge",
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR applying keyboard nudge: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return "break"
        self._log(f"Nudged {result['page']}.{result['widget']['id']} -> {result['op']['to']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)
        return "break"

    def _preview_hit_test(self, display_x: int, display_y: int) -> dict[str, Any] | None:
        context = self.last_context
        if not context or not self.preview_display:
            return None
        scene_x, scene_y = self._display_point_to_scene(display_x, display_y)
        page_id = context.get("input", {}).get("page_id")
        candidates = [
            widget
            for widget in context.get("widgets", [])
            if (not page_id or widget.get("page") == page_id)
            and self._point_in_scene_bbox(scene_x, scene_y, widget.get("bbox") or [])
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: int(item.get("z_index", 0)), reverse=True)
        return {**candidates[0], "kind": "widget"}

    def _select_widget_payload(self, payload: dict[str, Any]) -> None:
        item_id = f"widget:{payload['page']}:{payload.get('z_index', 0)}:{payload['id']}"
        if item_id in self.tree_payloads:
            self.object_tree.selection_set(item_id)
            self.object_tree.see(item_id)
        self._set_inspector(payload)
        self._set_property_target(payload)
        self._set_event_editor_target(payload)
        self._refresh_preview_overlays()

    def _dragged_bbox(self, drag: dict[str, Any], scene_x: int, scene_y: int) -> list[int]:
        old_x, old_y, old_w, old_h = [int(value) for value in drag["from"]]
        start_x, start_y = [int(value) for value in drag["start"]]
        if drag["mode"] == "resize":
            return [old_x, old_y, max(1, old_w + scene_x - start_x), max(1, old_h + scene_y - start_y)]
        return [old_x + scene_x - start_x, old_y + scene_y - start_y, old_w, old_h]

    def _draw_preview_temp_rect(self, scene_bbox: list[int]) -> None:
        if not isinstance(self.preview_label, tk.Canvas):
            return
        if self.preview_temp_rect is not None:
            self.preview_label.delete(self.preview_temp_rect)
        x0, y0, x1, y1 = self._scene_bbox_to_display(scene_bbox)
        self.preview_temp_rect = self.preview_label.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            outline="#111111",
            dash=(4, 2),
            width=2,
            tags=("overlay",),
        )

    def _scene_bbox_to_display(self, bbox: list[int]) -> tuple[int, int, int, int]:
        scale_x = float(self.preview_display.get("scale_x", 1.0))
        scale_y = float(self.preview_display.get("scale_y", 1.0))
        x, y, w, h = bbox
        return (
            int(round(x * scale_x)),
            int(round(y * scale_y)),
            int(round((x + w) * scale_x)),
            int(round((y + h) * scale_y)),
        )

    def _display_point_to_scene(self, x: int, y: int) -> tuple[int, int]:
        scale_x = float(self.preview_display.get("scale_x", 1.0))
        scale_y = float(self.preview_display.get("scale_y", 1.0))
        return int(round(x / max(scale_x, 0.001))), int(round(y / max(scale_y, 0.001)))

    def _point_in_scene_bbox(self, x: int, y: int, bbox: list[Any]) -> bool:
        if len(bbox) != 4:
            return False
        bx, by, bw, bh = [int(value) for value in bbox]
        return bx <= x <= bx + bw and by <= y <= by + bh

    def _near_resize_handle(self, x: int, y: int, bbox: list[int]) -> bool:
        bx, by, bw, bh = bbox
        return abs(x - (bx + bw)) <= 10 and abs(y - (by + bh)) <= 10

    def _on_tree_select(self, _event: tk.Event) -> None:
        selection = self.object_tree.selection()
        if not selection:
            return
        payloads = [self.tree_payloads[item] for item in selection if item in self.tree_payloads]
        widget_payloads = [item for item in payloads if item.get("kind") == "widget"]
        if len(widget_payloads) > 1:
            self._set_multi_widget_selection(widget_payloads)
            return
        payload = widget_payloads[0] if widget_payloads else (payloads[0] if payloads else None)
        if payload is not None:
            self._set_inspector(payload)
            self._set_property_target(payload)
            self._set_event_editor_target(payload)
            self._refresh_preview_overlays()

    def _set_multi_widget_selection(self, payloads: list[dict[str, Any]]) -> None:
        self.selected_widget_payload = None
        self.selected_widget_payloads = payloads
        self.selected_page_payload = None
        self.selected_event_owner = None
        pages = sorted({str(item.get("page")) for item in payloads})
        self.property_target_var.set(f"{len(payloads)} widgets selected")
        self.event_target_var.set("Multiple widgets selected")
        for var in self.property_vars.values():
            var.set("")
        for text in self.property_json_texts.values():
            self._replace_text(text, "")
        self._replace_text(self.events_text, "")
        self._set_inspector(
            {
                "kind": "multi-widget-selection",
                "count": len(payloads),
                "pages": pages,
                "widgets": [
                    {
                        "page": item.get("page"),
                        "id": item.get("id"),
                        "type": item.get("type"),
                        "bbox": item.get("bbox"),
                    }
                    for item in payloads
                ],
                "available_actions": [
                    "align left",
                    "align top",
                    "align horizontal center",
                    "align vertical center",
                    "distribute horizontal",
                    "distribute vertical",
                    "same width",
                    "same height",
                    "same size",
                ],
            }
        )
        self._refresh_preview_overlays()

    def _set_inspector(self, payload: dict[str, Any]) -> None:
        self._replace_text(self.inspector, json.dumps(payload, ensure_ascii=False, indent=2))

    def _set_property_target(self, payload: dict[str, Any]) -> None:
        if payload.get("kind") == "page":
            self.selected_widget_payload = None
            self.selected_widget_payloads = []
            self._set_page_settings(payload)
            self.property_target_var.set(f"Page {payload.get('id')}")
            for var in self.property_vars.values():
                var.set("")
            for text in self.property_json_texts.values():
                self._replace_text(text, "")
            self.toolbox_vars["page"].set(str(payload.get("id") or "page0"))
            return
        if payload.get("kind") != "widget":
            return
        self.selected_widget_payload = payload
        self.selected_widget_payloads = [payload]
        self.property_target_var.set(f"{payload.get('page')}.{payload.get('id')}")
        for key in ("id", "type", "x", "y", "w", "h", "text", "value"):
            value = payload.get(key)
            if value is None and key in {"x", "y", "w", "h"}:
                bbox = payload.get("bbox") or []
                index = {"x": 0, "y": 1, "w": 2, "h": 3}[key]
                value = bbox[index] if len(bbox) > index else None
            self.property_vars[key].set("" if value is None else str(value))
        for key, text in self.property_json_texts.items():
            value = payload.get(key) or {}
            self._replace_text(text, json.dumps(value, ensure_ascii=False, indent=2))

    def _reload_widget_properties(self) -> None:
        payload = self.selected_widget_payload
        if not payload:
            messagebox.showinfo(APP_TITLE, "Select a widget first.")
            return
        self._set_property_target(payload)

    def _save_widget_properties(self) -> None:
        payload = self.selected_widget_payload
        if not payload:
            messagebox.showinfo(APP_TITLE, "Select a widget first.")
            return
        try:
            updates = _widget_updates_from_vars(self.property_vars, self.property_json_texts)
            result = update_scene_widget(
                self.scene_var.get(),
                page_id=str(payload["page"]),
                widget_id=str(payload["id"]),
                updates=updates,
                rewrite_event_references=self.rewrite_widget_refs_var.get(),
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR saving properties: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Saved properties: {result['page']}.{result['widget']['id']} ({result['widget']['type']})")
        if result.get("rewritten_event_references"):
            self._log(f"Rewrote event references: {len(result['rewritten_event_references'])}")
        for warning in result.get("warnings", []):
            self._log(f"WARNING {warning.get('code')}: {warning.get('owner')} {warning.get('line')}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _add_widget_from_toolbox(self) -> None:
        try:
            widget = _widget_from_toolbox_vars(self.toolbox_vars, self.toolbox_json_texts)
            result = add_scene_widget(self.scene_var.get(), page_id=self.toolbox_vars["page"].get() or "page0", widget=widget)
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR adding widget: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Added widget: {result['page']}.{result['widget']['id']} ({result['widget']['type']})")
        self._suggest_toolbox_id()
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _load_toolbox_template(self) -> None:
        widget_type = self.toolbox_vars["type"].get() or "text"
        widget_id = self.toolbox_vars["id"].get().strip() or None
        try:
            template = get_widget_template(
                widget_type,
                widget_id=widget_id,
                x=_optional_int_var(self.toolbox_vars["x"]) or 40,
                y=_optional_int_var(self.toolbox_vars["y"]) or 40,
            )["widget"]
        except Exception as exc:  # noqa: BLE001 - GUI should surface template failures.
            self._log(f"ERROR loading widget template: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        for key in ("id", "type", "x", "y", "w", "h", "text", "value"):
            value = template.get(key)
            self.toolbox_vars[key].set("" if value is None else str(value))
        for key, text_widget in self.toolbox_json_texts.items():
            self._replace_text(text_widget, json.dumps(template.get(key) or {}, ensure_ascii=False, indent=2))
        self._log(f"Loaded widget template: {template['type']}")

    def _copy_selected_widget(self) -> None:
        payload = self._selected_widget_for_action()
        if not payload:
            return
        label = f"{payload.get('page')}.{payload.get('id')}"
        try:
            result = copy_scene_widget(self.scene_var.get(), page_id=str(payload["page"]), widget_id=str(payload["id"]))
        except Exception as exc:  # noqa: BLE001 - GUI should surface clipboard failures.
            self._log(f"ERROR copying widget {label}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.widget_clipboard = result["clipboard"]
        self._log(f"Copied widget: {label}")

    def _cut_selected_widget(self) -> None:
        payload = self._selected_widget_for_action()
        if not payload:
            return
        label = f"{payload.get('page')}.{payload.get('id')}"
        try:
            result = cut_scene_widget(self.scene_var.get(), page_id=str(payload["page"]), widget_id=str(payload["id"]))
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR cutting widget {label}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self.widget_clipboard = result["clipboard"]
        self.selected_widget_payload = None
        self._log(f"Cut widget: {label}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _paste_widget_clipboard(self) -> None:
        if not self.widget_clipboard or not isinstance(self.widget_clipboard.get("widget"), dict):
            messagebox.showinfo(APP_TITLE, "Copy a widget first.")
            return
        page_id = self._paste_target_page_id()
        if not page_id:
            messagebox.showinfo(APP_TITLE, "Select a target page or widget first.")
            return
        try:
            result = paste_scene_widget(
                self.scene_var.get(),
                page_id=page_id,
                widget=self.widget_clipboard["widget"],
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR pasting widget to {page_id}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        widget = result["widget"]
        self._log(f"Pasted widget: {result['page']}.{widget['id']} ({widget['type']})")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _paste_target_page_id(self) -> str | None:
        page = self.selected_page_payload
        if page and page.get("kind") == "page" and page.get("id"):
            return str(page["id"])
        widget = self.selected_widget_payload
        if widget and widget.get("kind") == "widget" and widget.get("page"):
            return str(widget["page"])
        try:
            scene = load_scene(self.scene_var.get())
        except Exception:
            return None
        return scene.project.get("default_page") or (scene.pages[0].id if scene.pages else None)

    def _delete_selected_widget(self) -> None:
        payload = self._selected_widget_for_action()
        if not payload:
            return
        label = f"{payload.get('page')}.{payload.get('id')}"
        if not messagebox.askyesno(APP_TITLE, f"Delete widget {label}?"):
            return
        try:
            result = delete_scene_widget(self.scene_var.get(), page_id=str(payload["page"]), widget_id=str(payload["id"]))
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR deleting widget {label}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        deleted = result["deleted_widget"]
        self.selected_widget_payload = None
        self._log(f"Deleted widget: {result['page']}.{deleted['id']} ({deleted['type']})")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _duplicate_selected_widget(self) -> None:
        payload = self._selected_widget_for_action()
        if not payload:
            return
        label = f"{payload.get('page')}.{payload.get('id')}"
        try:
            result = duplicate_scene_widget(self.scene_var.get(), page_id=str(payload["page"]), widget_id=str(payload["id"]))
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR duplicating widget {label}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        widget = result["widget"]
        self._log(f"Duplicated widget: {result['page']}.{widget['id']} ({widget['type']})")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _shortcut_delete_widget(self, _event: tk.Event) -> str:
        self._delete_selected_widget()
        return "break"

    def _shortcut_duplicate_widget(self, _event: tk.Event) -> str:
        self._duplicate_selected_widget()
        return "break"

    def _shortcut_copy_widget(self, _event: tk.Event) -> str:
        self._copy_selected_widget()
        return "break"

    def _shortcut_cut_widget(self, _event: tk.Event) -> str:
        self._cut_selected_widget()
        return "break"

    def _shortcut_paste_widget(self, _event: tk.Event) -> str:
        self._paste_widget_clipboard()
        return "break"

    def _move_selected_widget(self, direction: str) -> None:
        payload = self._selected_widget_for_action()
        if not payload:
            return
        label = f"{payload.get('page')}.{payload.get('id')}"
        try:
            result = move_scene_widget(self.scene_var.get(), page_id=str(payload["page"]), widget_id=str(payload["id"]), direction=direction)
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR moving widget {label}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Moved widget: {label} {result['old_z_index']} -> {result['z_index']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _align_selected_widgets(self, edge: str) -> None:
        payloads = self._selected_widget_payloads_from_tree() or self.selected_widget_payloads
        if len(payloads) < 2:
            messagebox.showinfo(APP_TITLE, "Select at least two widgets on the same page.")
            return
        pages = {str(item.get("page")) for item in payloads}
        if len(pages) != 1:
            messagebox.showinfo(APP_TITLE, "Align only supports widgets on one page.")
            return
        page_id = next(iter(pages))
        widget_ids = [str(item.get("id")) for item in payloads if item.get("id")]
        try:
            result = design_align_widgets(
                self.scene_var.get(),
                self.out_var.get(),
                page_id=page_id,
                widget_ids=widget_ids,
                edge=edge,
                anchor="first",
                snap=self._design_snap(),
                source=f"gui-align-{edge}",
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR aligning widgets: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(
            f"Aligned {len(result['widgets'])} widgets on {page_id}: "
            f"edge={edge} target={result['op']['target']}"
        )
        self._log(f"Agent patch: {result['outputs']['agent_patch_json']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _distribute_selected_widgets(self, axis: str) -> None:
        payloads = self._selected_widget_payloads_from_tree() or self.selected_widget_payloads
        if len(payloads) < 3:
            messagebox.showinfo(APP_TITLE, "Select at least three widgets on the same page.")
            return
        pages = {str(item.get("page")) for item in payloads}
        if len(pages) != 1:
            messagebox.showinfo(APP_TITLE, "Distribute only supports widgets on one page.")
            return
        page_id = next(iter(pages))
        widget_ids = [str(item.get("id")) for item in payloads if item.get("id")]
        try:
            result = design_distribute_widgets(
                self.scene_var.get(),
                self.out_var.get(),
                page_id=page_id,
                widget_ids=widget_ids,
                axis=axis,
                snap=self._design_snap(),
                source=f"gui-distribute-{axis}",
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR distributing widgets: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(
            f"Distributed {len(result['widgets'])} widgets on {page_id}: "
            f"axis={axis} step={result['op']['step']:.2f}"
        )
        self._log(f"Agent patch: {result['outputs']['agent_patch_json']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _match_size_selected_widgets(self, mode: str) -> None:
        payloads = self._selected_widget_payloads_from_tree() or self.selected_widget_payloads
        if len(payloads) < 2:
            messagebox.showinfo(APP_TITLE, "Select at least two widgets on the same page.")
            return
        pages = {str(item.get("page")) for item in payloads}
        if len(pages) != 1:
            messagebox.showinfo(APP_TITLE, "Same-size only supports widgets on one page.")
            return
        page_id = next(iter(pages))
        widget_ids = [str(item.get("id")) for item in payloads if item.get("id")]
        try:
            result = design_match_size_widgets(
                self.scene_var.get(),
                self.out_var.get(),
                page_id=page_id,
                widget_ids=widget_ids,
                mode=mode,
                anchor="first",
                source=f"gui-match-size-{mode}",
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR matching widget size: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(
            f"Matched size for {len(result['widgets'])} widgets on {page_id}: "
            f"mode={mode} target={result['op']['target_size']}"
        )
        self._log(f"Agent patch: {result['outputs']['agent_patch_json']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _selected_widget_for_action(self) -> dict[str, Any] | None:
        payloads = self._selected_widget_payloads_from_tree()
        if len(payloads) > 1:
            messagebox.showinfo(APP_TITLE, "Select exactly one widget for this action.")
            return None
        payload = payloads[0] if payloads else self.selected_widget_payload
        if not payload or payload.get("kind") != "widget":
            messagebox.showinfo(APP_TITLE, "Select a widget first.")
            return None
        return payload

    def _selected_widget_payloads_from_tree(self) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for item_id in self.object_tree.selection():
            payload = self.tree_payloads.get(item_id)
            if payload and payload.get("kind") == "widget":
                payloads.append(payload)
        return payloads

    def _design_snap(self) -> int:
        try:
            return max(1, int(self.snap_var.get() or "1"))
        except ValueError:
            self.snap_var.set("1")
            return 1

    def _add_page(self) -> None:
        try:
            page_id = self._suggest_page_id()
            result = add_scene_page(self.scene_var.get(), page_id=page_id)
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR adding page: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Added page: {result['page']['id']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _duplicate_selected_page(self) -> None:
        payload = self._selected_page_for_action()
        if not payload:
            return
        try:
            result = duplicate_scene_page(self.scene_var.get(), page_id=str(payload["id"]))
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR duplicating page {payload.get('id')}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Duplicated page: {result['source_page']} -> {result['page']['id']}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _delete_selected_page(self) -> None:
        payload = self._selected_page_for_action()
        if not payload:
            return
        page_id = str(payload["id"])
        if not messagebox.askyesno(APP_TITLE, f"Delete page {page_id}?"):
            return
        try:
            result = delete_scene_page(self.scene_var.get(), page_id=page_id)
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR deleting page {page_id}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Deleted page: {result['deleted_page']['id']}; default_page={result.get('default_page')}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _preview_selected_page(self) -> None:
        payload = self._selected_page_for_action()
        if not payload:
            return
        self.selected_page_payload = payload
        self._generate(build_tft=False)

    def _selected_page_for_action(self) -> dict[str, Any] | None:
        selection = self.object_tree.selection()
        payload = self.tree_payloads.get(selection[0]) if selection else self.selected_page_payload
        if not payload or payload.get("kind") != "page":
            messagebox.showinfo(APP_TITLE, "Select a page first.")
            return None
        return payload

    def _selected_preview_page_id(self) -> str | None:
        widget = self.selected_widget_payload
        if widget and widget.get("kind") == "widget" and widget.get("page"):
            return str(widget["page"])
        page = self.selected_page_payload
        if page and page.get("kind") == "page" and page.get("id"):
            return str(page["id"])
        return None

    def _suggest_page_id(self) -> str:
        try:
            scene = load_scene(self.scene_var.get())
            existing = {page.id for page in scene.pages}
        except Exception:
            existing = set()
        index = 0
        while f"page{index}" in existing:
            index += 1
        return f"page{index}"

    def _suggest_toolbox_id(self) -> None:
        widget_type = self.toolbox_vars["type"].get() or "text"
        prefix = _widget_id_prefix(widget_type)
        try:
            scene = load_scene(self.scene_var.get())
            page = next((item for item in scene.pages if item.id == (self.toolbox_vars["page"].get() or "page0")), None)
            existing = {widget.id for widget in page.widgets} if page else set()
        except Exception:
            existing = set()
        index = 0
        while f"{prefix}{index}" in existing:
            index += 1
        self.toolbox_vars["id"].set(f"{prefix}{index}")

    def _set_event_editor_target(self, payload: dict[str, Any]) -> None:
        if payload.get("kind") not in {"page", "widget"}:
            return
        self.selected_event_owner = payload
        if payload.get("kind") == "page":
            self.event_target_var.set(str(payload.get("id")))
            if self.event_name_var.get() not in {"load", "loadend", "unload"}:
                self.event_name_var.set("load")
        else:
            self.event_target_var.set(f"{payload.get('page')}.{payload.get('id')}")
            if self.event_name_var.get() not in EVENT_NAMES:
                self.event_name_var.set("down")
        self._refresh_event_editor()

    def _selected_event_path(self) -> str | None:
        owner = self.selected_event_owner
        if not owner:
            return None
        event_name = self.event_name_var.get()
        if event_name not in EVENT_NAMES:
            return None
        if owner.get("kind") == "page":
            return f"{owner.get('id')}.{event_name}"
        return f"{owner.get('page')}.{owner.get('id')}.{event_name}"

    def _refresh_event_editor(self) -> None:
        event_path = self._selected_event_path()
        if not event_path:
            return
        try:
            slot = get_scene_event(self.scene_var.get(), event_path)
        except Exception as exc:  # noqa: BLE001 - GUI should keep the edit pane usable.
            self._replace_text(self.events_text, "")
            self._log(f"ERROR reading event {event_path}: {exc}")
            return
        self._replace_text(self.events_text, "\n".join(slot["lines"]))
        self._log(f"Loaded event {event_path}: {slot['line_count']} line(s)")

    def _save_selected_event(self) -> None:
        event_path = self._selected_event_path()
        if not event_path:
            messagebox.showinfo(APP_TITLE, "Select a page or object first.")
            return
        lines = [line.rstrip() for line in self.events_text.get("1.0", "end").splitlines() if line.strip()]
        try:
            if lines:
                slot = set_scene_event(self.scene_var.get(), event_path, lines)
            else:
                slot = clear_scene_event(self.scene_var.get(), event_path)
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR saving event {event_path}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._log(f"Saved event {event_path}: {slot['line_count']} line(s)")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _insert_event_snippet(self) -> None:
        label = self.event_snippet_var.get()
        snippet = next((item for item in self.event_snippets if item.get("label") == label), None)
        if not snippet:
            return
        template = self._contextual_event_snippet_template(snippet)
        current = self.events_text.get("1.0", "end-1c")
        prefix = "" if not current or current.endswith("\n") else "\n"
        self.events_text.insert("end", f"{prefix}{template}\n")
        self.events_text.see("end")
        self._log(f"Inserted event snippet: {snippet['id']} -> {template}")

    def _move_event_line_up(self) -> None:
        self._move_event_line(-1)

    def _move_event_line_down(self) -> None:
        self._move_event_line(1)

    def _move_event_line(self, delta: int) -> None:
        lines = self._event_editor_lines()
        if len(lines) < 2:
            return
        index = self._event_editor_current_line_index(len(lines))
        target = index + delta
        if target < 0 or target >= len(lines):
            return
        lines[index], lines[target] = lines[target], lines[index]
        self._replace_event_editor_lines(lines, target)
        self._log(f"Moved event line {index + 1} -> {target + 1}")

    def _delete_event_line(self) -> None:
        lines = self._event_editor_lines()
        if not lines:
            return
        index = self._event_editor_current_line_index(len(lines))
        removed = lines.pop(index)
        focus_index = min(index, max(len(lines) - 1, 0))
        self._replace_event_editor_lines(lines, focus_index)
        self._log(f"Deleted event line {index + 1}: {removed}")

    def _event_editor_lines(self) -> list[str]:
        return [line.rstrip() for line in self.events_text.get("1.0", "end").splitlines() if line.strip()]

    def _event_editor_current_line_index(self, line_count: int) -> int:
        try:
            row = int(self.events_text.index("insert").split(".", 1)[0]) - 1
        except Exception:  # noqa: BLE001 - fall back to the first line for GUI editing.
            row = 0
        return min(max(row, 0), max(line_count - 1, 0))

    def _replace_event_editor_lines(self, lines: list[str], focus_index: int) -> None:
        text = "\n".join(lines)
        if text:
            text += "\n"
        self._replace_text(self.events_text, text)
        if lines:
            row = min(max(focus_index, 0), len(lines) - 1) + 1
            self.events_text.mark_set("insert", f"{row}.0")
            self.events_text.see(f"{row}.0")

    def _contextual_event_snippet_template(self, snippet: dict[str, Any]) -> str:
        template = str(snippet.get("template", ""))
        page_id = self._selected_event_page_id()
        object_id = self._default_event_object_id(page_id)
        if "<page_id>" in template:
            template = template.replace("<page_id>", self._default_event_page_target(page_id))
        if "<object_id>" in template:
            template = template.replace("<object_id>", object_id)
        return template

    def _selected_event_page_id(self) -> str | None:
        owner = self.selected_event_owner or {}
        if owner.get("kind") == "page":
            return str(owner.get("id"))
        if owner.get("page"):
            return str(owner.get("page"))
        return None

    def _default_event_page_target(self, current_page: str | None) -> str:
        page_ids = self._scene_page_ids()
        for page_id in page_ids:
            if page_id != current_page:
                return page_id
        return current_page or (page_ids[0] if page_ids else "page0")

    def _default_event_object_id(self, page_id: str | None) -> str:
        widgets = self._scene_widget_ids(page_id)
        owner = self.selected_event_owner or {}
        selected_id = str(owner.get("id")) if owner.get("kind") == "widget" and owner.get("id") else None
        for widget_id in widgets:
            if widget_id != selected_id:
                return widget_id
        return selected_id or (widgets[0] if widgets else "obj0")

    def _scene_page_ids(self) -> list[str]:
        try:
            return [page.id for page in load_scene(self.scene_var.get()).pages]
        except Exception:  # noqa: BLE001 - snippet fallback should keep the editor responsive.
            context = self.last_context or {}
            return [str(item.get("id")) for item in context.get("pages", []) if item.get("id")]

    def _scene_widget_ids(self, page_id: str | None) -> list[str]:
        try:
            scene = load_scene(self.scene_var.get())
            for page in scene.pages:
                if page_id is None or page.id == page_id:
                    return [widget.id for widget in page.widgets]
        except Exception:  # noqa: BLE001 - snippet fallback should keep the editor responsive.
            pass
        context = self.last_context or {}
        return [
            str(item.get("id"))
            for item in context.get("widgets", [])
            if item.get("id") and (page_id is None or item.get("page") == page_id)
        ]

    def _clear_selected_event(self) -> None:
        event_path = self._selected_event_path()
        if not event_path:
            messagebox.showinfo(APP_TITLE, "Select a page or object first.")
            return
        try:
            clear_scene_event(self.scene_var.get(), event_path)
        except Exception as exc:  # noqa: BLE001 - GUI should surface edit failures.
            self._log(f"ERROR clearing event {event_path}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        self._replace_text(self.events_text, "")
        self._log(f"Cleared event {event_path}")
        self._load_scene_outline(silent=True)
        self._generate(build_tft=False)

    def _simulate_selected_event(self) -> None:
        event_path = self._selected_event_path()
        if not event_path:
            messagebox.showinfo(APP_TITLE, "Select a page or object first.")
            return
        lines = [line.rstrip() for line in self.events_text.get("1.0", "end").splitlines() if line.strip()]
        try:
            if lines:
                set_scene_event(self.scene_var.get(), event_path, lines)
            else:
                clear_scene_event(self.scene_var.get(), event_path)
            result = simulate_scene_event(
                self.scene_var.get(),
                event_path,
                out_dir=Path(self.out_var.get()).expanduser() / "event_sim",
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface simulation failures.
            self._log(f"ERROR simulating event {event_path}: {exc}")
            messagebox.showerror(APP_TITLE, str(exc))
            return
        summary = result.get("summary", {})
        outputs = result.get("outputs", {})
        self._log(
            f"Simulated event {event_path}: "
            f"ok={summary.get('ok')} final={summary.get('final_page')} "
            f"lines={summary.get('executed_line_count')} diagnostics={len(result.get('diagnostics', []))}"
        )
        if outputs:
            self._log(f"Simulation report: {outputs.get('simulation_report_json')}")
        self._set_inspector(
            {
                "event_simulation": {
                    "event_path": event_path,
                    "summary": summary,
                    "outputs": outputs,
                    "safe_to_flash": result.get("safe_to_flash"),
                    "not_claimed": result.get("not_claimed"),
                }
            }
        )
        self._update_diagnostics(result.get("diagnostics", []))
        self._load_scene_outline(silent=True)

    def _set_agent_text(self, context: dict[str, Any] | None) -> None:
        if not context:
            text = (
                "Agent contract:\n"
                "- Edit the scene JSON/YAML, not the GUI state.\n"
                "- Run Preview Bundle to produce agent_context.json.\n"
                "- Hardware upload is a separate explicit operation."
            )
            self._replace_text(self.agent_text, text)
            return
        agent_interface = context.get("agent_interface", {})
        policy = context.get("hardware_policy", {})
        outputs = context.get("outputs", {})
        safe_commands = "\n".join(f"- {item}" for item in agent_interface.get("safe_commands", []))
        dangerous = "\n".join(f"- {item.get('command')} :: {item.get('reason')}" for item in agent_interface.get("dangerous_commands", []))
        text = (
            "Agent-readable artifacts\n"
            f"agent_context: {outputs.get('agent_context_json')}\n"
            f"diagnostics: {outputs.get('diagnostics_json')}\n"
            f"capabilities: {outputs.get('capability_report_json')}\n"
            f"manifest: {outputs.get('build_manifest_json')}\n\n"
            "Safe commands\n"
            f"{safe_commands}\n\n"
            "Dangerous commands\n"
            f"{dangerous}\n\n"
            "Hardware policy\n"
            f"{json.dumps(policy, ensure_ascii=False, indent=2)}"
        )
        self._replace_text(self.agent_text, text)

    def _replace_text(self, widget: tk.Text, text: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("end", text)

    def _load_preview(self, path: Path, label: ttk.Label, label_name: str) -> None:
        original = Image.open(path).convert("RGB")
        source_width, source_height = original.size
        image = original.copy()
        image.thumbnail((620, 460))
        photo = ImageTk.PhotoImage(image)
        if label_name == "preview":
            self.preview_image = photo
            if isinstance(label, tk.Canvas):
                label.delete("all")
                label.configure(width=max(620, image.width), height=max(460, image.height))
                label.create_image(0, 0, anchor="nw", image=photo, tags=("preview_image",))
                self.preview_display = {
                    "source_width": source_width,
                    "source_height": source_height,
                    "display_width": image.width,
                    "display_height": image.height,
                    "scale_x": image.width / max(1, source_width),
                    "scale_y": image.height / max(1, source_height),
                }
                self._refresh_preview_overlays()
                return
        else:
            self.annotated_image = photo
        label.configure(image=photo, text="")

    def _open_context_output(self, key: str, fallback_name: str) -> None:
        context = self.last_context
        path = Path(context["outputs"][key]) if context else Path(self.out_var.get()) / fallback_name
        if path.exists():
            os.startfile(path)
        else:
            messagebox.showinfo(APP_TITLE, "Generate a preview bundle first.")

    def _open_output_dir(self) -> None:
        out_dir = Path(self.out_var.get())
        out_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(out_dir)

    def _log(self, message: str) -> None:
        self.log.insert("end", message + "\n")
        self.log.see("end")


def _default_repo_root() -> Path:
    candidates = [
        Path.cwd(),
        Path.home() / "Documents" / "Codex" / "2026-05-03" / "files-mentioned-by-the-user-delay",
    ]
    for candidate in candidates:
        if (candidate / "usarthmi").exists() and (candidate / "examples").exists():
            return candidate.resolve()
    return Path.cwd().resolve()


def _widget_type_options() -> list[str]:
    return sorted(
        item["type"]
        for item in list_widget_capabilities()
        if item.get("support") in {"supported", "pending"}
    )


def _widget_updates_from_vars(vars_by_key: dict[str, tk.StringVar], json_texts: dict[str, tk.Text]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for key in ("id", "type", "text"):
        value = vars_by_key[key].get()
        updates[key] = value if value else None
    for key in ("x", "y", "w", "h", "value"):
        value = vars_by_key[key].get().strip()
        updates[key] = int(value, 0) if value else None
    for key in ("style", "resources", "bindings"):
        updates[key] = _json_text_map(json_texts[key], key)
    return updates


def _widget_from_toolbox_vars(vars_by_key: dict[str, tk.StringVar], json_texts: dict[str, tk.Text]) -> dict[str, Any]:
    widget: dict[str, Any] = {
        "id": vars_by_key["id"].get().strip(),
        "type": vars_by_key["type"].get().strip(),
    }
    for key in ("x", "y", "w", "h", "value"):
        value = vars_by_key[key].get().strip()
        if value:
            widget[key] = int(value, 0)
    text = vars_by_key["text"].get()
    if text:
        widget["text"] = text
    for key in ("style", "resources", "bindings"):
        value = _json_text_map(json_texts[key], key)
        if value:
            widget[key] = value
    return widget


def _asset_from_vars(vars_by_key: dict[str, tk.StringVar]) -> dict[str, Any]:
    asset: dict[str, Any] = {}
    for key in ("id", "source", "normal", "pressed", "disabled"):
        value = vars_by_key[key].get().strip()
        if value:
            asset[key] = value
    return asset


def _optional_int_var(var: tk.StringVar) -> int | None:
    value = var.get().strip()
    return int(value, 0) if value else None


def _is_text_input_widget(widget: tk.Widget) -> bool:
    try:
        widget_class = widget.winfo_class()
    except tk.TclError:
        return False
    return widget_class in {"Entry", "TEntry", "Text", "Combobox", "TCombobox", "Spinbox", "TSpinbox"}


def _json_text_map(widget: tk.Text, label: str) -> dict[str, Any]:
    raw = widget.get("1.0", "end").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be a JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _widget_id_prefix(widget_type: str) -> str:
    mapping = {
        "text": "t",
        "button": "b",
        "image": "p",
        "number": "n",
        "timer": "tm",
        "progress": "j",
        "slider": "h",
        "waveform": "s",
        "file-browser": "fbrowser",
        "file-stream": "fs",
        "data-record": "data",
        "text-select": "select",
        "sliding-text": "slt",
    }
    return mapping.get(widget_type, "".join(ch for ch in widget_type if ch.isalnum())[:8] or "w")


if __name__ == "__main__":
    main()
