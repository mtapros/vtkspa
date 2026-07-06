"""Very basic Tkinter GUI for VTK SPA.

Launch with ``vtkspa gui`` (or ``python -m vtkspa.gui``). Provides:
- template selection + validation
- single render with live preview
- batch render from CSV with a progress log

Uses only the standard library (tkinter) plus Pillow, which is already a
dependency, so no extra packages are required.
"""
from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

PREVIEW_MAX = (520, 520)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("VTK SPA — Sports Photo Automation")
        self.geometry("980x640")
        self.minsize(820, 520)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._preview_photo = None  # keep a reference so Tk doesn't GC it
        self._busy = False

        self._build_ui()
        self.after(100, self._drain_log_queue)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        # Template row (shared by both tabs)
        top = ttk.Frame(root)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="Template dir:").pack(side=tk.LEFT)
        self.template_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.template_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(top, text="Browse…", command=self._pick_template).pack(side=tk.LEFT)
        ttk.Button(top, text="Validate", command=self._validate_template).pack(side=tk.LEFT, padx=(6, 0))

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True)
        notebook.add(self._build_render_tab(notebook), text="Single Render")
        notebook.add(self._build_batch_tab(notebook), text="Batch Render")

        # Log area
        log_frame = ttk.LabelFrame(root, text="Log", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _build_render_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(parent, padding=8)
        left = ttk.Frame(tab)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.photo_var = tk.StringVar()
        self._file_row(left, "Photo:", self.photo_var, self._pick_photo)

        ttk.Label(left, text="Data (JSON):").pack(anchor=tk.W, pady=(8, 2))
        self.data_text = tk.Text(left, width=42, height=8)
        self.data_text.insert("1.0", '{\n  "name": "Jane Smith",\n  "team": "Red Sox",\n  "number": "23"\n}')
        self.data_text.pack(fill=tk.X)

        btns = ttk.Frame(left)
        btns.pack(fill=tk.X, pady=8)
        ttk.Button(btns, text="Preview", command=self._do_preview).pack(side=tk.LEFT)
        ttk.Button(btns, text="Render & Save…", command=self._do_render_save).pack(side=tk.LEFT, padx=6)

        right = ttk.LabelFrame(tab, text="Preview", padding=4)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.preview_label = ttk.Label(right, text="(no preview)", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        return tab

    def _build_batch_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(parent, padding=8)

        self.csv_var = tk.StringVar()
        self._file_row(tab, "Roster CSV:", self.csv_var, self._pick_csv)
        self.photos_dir_var = tk.StringVar()
        self._file_row(tab, "Photos dir:", self.photos_dir_var, self._pick_photos_dir)
        self.output_dir_var = tk.StringVar()
        self._file_row(tab, "Output dir:", self.output_dir_var, self._pick_output_dir)

        opts = ttk.Frame(tab)
        opts.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(opts, text="JPEG quality:").pack(side=tk.LEFT)
        self.quality_var = tk.IntVar(value=95)
        ttk.Spinbox(opts, from_=1, to=100, width=5, textvariable=self.quality_var).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Label(opts, text="Filename pattern:").pack(side=tk.LEFT)
        self.pattern_var = tk.StringVar(value="{name_slug}_{template_name}")
        ttk.Entry(opts, textvariable=self.pattern_var, width=32).pack(side=tk.LEFT, padx=4)

        run_row = ttk.Frame(tab)
        run_row.pack(fill=tk.X, pady=10)
        self.batch_button = ttk.Button(run_row, text="Run Batch", command=self._do_batch)
        self.batch_button.pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(run_row, mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        return tab

    def _file_row(self, parent: tk.Widget, label: str, var: tk.StringVar, command) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=12).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(row, text="Browse…", command=command).pack(side=tk.LEFT)

    # ------------------------------------------------------------- pickers
    def _pick_template(self) -> None:
        path = filedialog.askdirectory(title="Select template directory")
        if path:
            self.template_var.set(path)

    def _pick_photo(self) -> None:
        path = filedialog.askopenfilename(
            title="Select subject photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.tif *.tiff"), ("All files", "*.*")],
        )
        if path:
            self.photo_var.set(path)

    def _pick_csv(self) -> None:
        path = filedialog.askopenfilename(title="Select roster CSV", filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if path:
            self.csv_var.set(path)

    def _pick_photos_dir(self) -> None:
        path = filedialog.askdirectory(title="Select photos directory")
        if path:
            self.photos_dir_var.set(path)

    def _pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Select output directory")
        if path:
            self.output_dir_var.set(path)

    # ------------------------------------------------------------- logging
    def log(self, message: str) -> None:
        """Thread-safe log append."""
        self._log_queue.put(message)

    def _drain_log_queue(self) -> None:
        try:
            while True:
                message = self._log_queue.get_nowait()
                self.log_text.configure(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    # ------------------------------------------------------------- actions
    def _require_template(self) -> Path | None:
        path = self.template_var.get().strip()
        if not path:
            messagebox.showerror("VTK SPA", "Please select a template directory first.")
            return None
        return Path(path)

    def _validate_template(self) -> None:
        template_dir = self._require_template()
        if template_dir is None:
            return
        from vtkspa.template.schema import load_template, validate_template

        try:
            template = load_template(template_dir)
            errors = validate_template(template, template_dir)
        except Exception as exc:
            self.log(f"✗ Could not load template: {exc}")
            messagebox.showerror("VTK SPA", f"Could not load template:\n{exc}")
            return
        if errors:
            self.log(f"✗ Validation failed: {len(errors)} issue(s)")
            for error in errors:
                self.log(f"  • {error}")
            messagebox.showerror("VTK SPA", "Template validation failed:\n" + "\n".join(errors))
        else:
            self.log(f"✓ Template valid: {template.name!r} ({len(template.layers)} layers)")
            messagebox.showinfo("VTK SPA", f"Template valid: {template.name!r} ({len(template.layers)} layers)")

    def _parse_data(self) -> dict | None:
        raw = self.data_text.get("1.0", tk.END).strip() or "{}"
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("data must be a JSON object")
            return data
        except Exception as exc:
            messagebox.showerror("VTK SPA", f"Invalid JSON data:\n{exc}")
            return None

    def _render_once(self):
        """Render a single composite from current form values (returns PIL Image)."""
        from vtkspa.render.engine import RenderEngine
        from vtkspa.template.schema import load_template

        template_dir = self._require_template()
        if template_dir is None:
            return None
        data = self._parse_data()
        if data is None:
            return None
        photo = self.photo_var.get().strip() or None
        template = load_template(template_dir)
        engine = RenderEngine()
        return engine.render(template=template, template_dir=template_dir, data_context=data, photo_path=photo)

    def _do_preview(self) -> None:
        try:
            img = self._render_once()
        except Exception as exc:
            self.log(f"✗ Render failed: {exc}")
            messagebox.showerror("VTK SPA", f"Render failed:\n{exc}")
            return
        if img is None:
            return
        self._show_preview(img)
        self.log("✓ Preview rendered")

    def _show_preview(self, img) -> None:
        from PIL import ImageTk

        thumb = img.copy()
        thumb.thumbnail(PREVIEW_MAX)
        self._preview_photo = ImageTk.PhotoImage(thumb.convert("RGB"))
        self.preview_label.configure(image=self._preview_photo, text="")

    def _do_render_save(self) -> None:
        try:
            img = self._render_once()
        except Exception as exc:
            self.log(f"✗ Render failed: {exc}")
            messagebox.showerror("VTK SPA", f"Render failed:\n{exc}")
            return
        if img is None:
            return
        output = filedialog.asksaveasfilename(
            title="Save render as",
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")],
        )
        if not output:
            return
        from vtkspa.render.engine import RenderEngine

        RenderEngine().save(img, output)
        self._show_preview(img)
        self.log(f"✓ Rendered: {output}")

    def _do_batch(self) -> None:
        if self._busy:
            return
        template_dir = self._require_template()
        if template_dir is None:
            return
        csv_path = self.csv_var.get().strip()
        photos_dir = self.photos_dir_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        if not (csv_path and photos_dir and output_dir):
            messagebox.showerror("VTK SPA", "Please select a roster CSV, photos directory, and output directory.")
            return

        self._busy = True
        self.batch_button.configure(state=tk.DISABLED)
        self.progress.configure(value=0)
        thread = threading.Thread(
            target=self._batch_worker,
            args=(template_dir, csv_path, photos_dir, output_dir, self.quality_var.get(), self.pattern_var.get()),
            daemon=True,
        )
        thread.start()

    def _step_progress(self) -> None:
        self.after(0, lambda: self.progress.step(1))

    def _batch_worker(self, template_dir, csv_path, photos_dir, output_dir, quality, pattern) -> None:
        from vtkspa.batch import BatchOptions, run_batch

        options = BatchOptions(jpeg_quality=quality, output_pattern=pattern, continue_on_error=True)

        def row_name(row, index):
            return row.data.get("name", row.data.get("first_name", f"row {index}"))

        def on_done(index, row, path):
            self.log(f"  [{index + 1}] ✓ {row_name(row, index)!r} → {path}")
            self._step_progress()

        def on_fail(index, row, exc):
            self.log(f"  [{index + 1}] ✗ {row_name(row, index)!r}: {exc}")
            self._step_progress()

        self.log(f"Starting batch render...\n  Template: {template_dir}\n  CSV: {csv_path}\n  Photos: {photos_dir}\n  Output: {output_dir}")
        try:
            from vtkspa.data.roster import parse_csv

            total = max(len(parse_csv(csv_path)), 1)
            self.after(0, lambda: self.progress.configure(maximum=total, value=0))
            result = run_batch(
                template_path=template_dir,
                csv_path=csv_path,
                photos_dir=photos_dir,
                output_dir=output_dir,
                options=options,
                on_row_done=on_done,
                on_row_fail=on_fail,
            )
        except Exception as exc:
            self.log(f"✗ Batch failed: {exc}")
            self.after(0, self._batch_finished)
            return

        self.log(f"Batch complete: {len(result.successes)} succeeded, {len(result.failures)} failed ({result.elapsed_seconds:.1f}s)")
        if result.unmatched_rows:
            self.log(f"  ⚠ {len(result.unmatched_rows)} rows without photos")
        if result.unmatched_photos:
            self.log(f"  ⚠ {len(result.unmatched_photos)} photos unmatched")
        self.log(f"  Report: {Path(output_dir) / 'batch_report.json'}")
        self.after(0, self._batch_finished)

    def _batch_finished(self) -> None:
        self._busy = False
        self.batch_button.configure(state=tk.NORMAL)


def main() -> None:
    try:
        app = App()
    except tk.TclError as exc:
        raise SystemExit(
            f"Could not start the GUI ({exc}).\n"
            "Make sure a display is available and tkinter is installed "
            "(e.g. `sudo apt install python3-tk` on Debian/Ubuntu)."
        )
    app.mainloop()


if __name__ == "__main__":
    main()
