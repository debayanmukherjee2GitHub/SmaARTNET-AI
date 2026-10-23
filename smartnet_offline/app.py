"""Small, local-only desktop interface for reviewing SmartNET inventories."""

from __future__ import annotations

import tkinter as tk
import threading
from queue import Queue
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from blueprint import build_blueprint, list_local_models
from inventory import InventoryError, load_inventory


class SmartNetApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SmaARTNET-AI | Offline Inventory")
        self.geometry("1080x700")
        self.minsize(760, 500)
        self.configure(bg="#f4f7fb")
        self.headers: list[str] = []
        self.records: list[dict[str, str]] = []
        self.selected_path: Path | None = None
        self.output_path = Path.home() / "Documents" / "SmaARTNET-AI_Output"
        self.result_queue: Queue[tuple[bool, object]] = Queue()
        self.busy = False
        self._style()
        self._layout()

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f7fb")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f4f7fb", foreground="#16253d", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 22), foreground="#10213b")
        style.configure("Muted.TLabel", foreground="#5b6c83")
        style.configure("CardValue.TLabel", background="#ffffff", font=("Segoe UI Semibold", 19), foreground="#155eef")
        style.configure("CardName.TLabel", background="#ffffff", foreground="#63738a")
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(16, 10))
        style.map("Accent.TButton", background=[("!disabled", "#155eef"), ("active", "#0f4dcc")], foreground=[("!disabled", "white")])
        style.configure("Treeview", rowheight=29, font=("Segoe UI", 9), background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#edf2fa", foreground="#32445f")

    def _layout(self) -> None:
        outer = ttk.Frame(self, padding=(28, 24))
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="SmaARTNET-AI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Offline inventory workspace", style="Muted.TLabel").pack(anchor="w", pady=(2, 20))

        action = ttk.Frame(outer)
        action.pack(fill="x", pady=(0, 18))
        ttk.Button(action, text="Open inventory file", style="Accent.TButton", command=self._choose_file).pack(side="left")
        self.file_label = ttk.Label(action, text="No file selected", style="Muted.TLabel")
        self.file_label.pack(side="left", padx=14)

        options = ttk.Frame(outer)
        options.pack(fill="x", pady=(0, 18))
        ttk.Label(options, text="Local Ollama model").grid(row=0, column=0, sticky="w")
        self.model_entry = ttk.Combobox(options, width=24)
        self.model_entry.grid(row=0, column=1, sticky="w", padx=(10, 18))
        ttk.Button(options, text="Find local models", command=self._refresh_models).grid(row=0, column=2, sticky="w")
        ttk.Label(options, text="Optional; leave blank for the rule-based report.", style="Muted.TLabel").grid(row=0, column=3, sticky="w", padx=(12, 0))
        ttk.Button(options, text="Output folder", command=self._choose_output).grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.output_label = ttk.Label(options, text=str(self.output_path), style="Muted.TLabel")
        self.output_label.grid(row=1, column=1, columnspan=4, sticky="w", padx=(10, 0), pady=(10, 0))
        options.columnconfigure(3, weight=1)

        cards = ttk.Frame(outer)
        cards.pack(fill="x", pady=(0, 18))
        self.row_count = self._card(cards, "Inventory rows", "—")
        self.column_count = self._card(cards, "Columns", "—")
        self.blank_count = self._card(cards, "Blank cells", "—")

        panel = ttk.Frame(outer, style="Card.TFrame", padding=14)
        panel.pack(fill="both", expand=True)
        header = ttk.Frame(panel, style="Card.TFrame")
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="Inventory preview", style="CardName.TLabel", font=("Segoe UI Semibold", 12)).pack(side="left")
        ttk.Label(header, text="First 100 rows", style="CardName.TLabel").pack(side="right")

        table_frame = ttk.Frame(panel, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)
        self.table = ttk.Treeview(table_frame, show="headings")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.status = ttk.Label(outer, text="Ready. Files are processed locally on this computer.", style="Muted.TLabel")
        self.status.pack(anchor="w", pady=(12, 0))
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(8, 0))
        self.progress.pack_forget()
        self.generate_button = ttk.Button(outer, text="Generate offline blueprint", style="Accent.TButton", command=self._generate)
        self.generate_button.pack(anchor="e", pady=(10, 0))

    @staticmethod
    def _card(parent: ttk.Frame, name: str, value: str) -> ttk.Label:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(16, 13))
        frame.pack(side="left", fill="x", expand=True, padx=(0, 12))
        ttk.Label(frame, text=name, style="CardName.TLabel").pack(anchor="w")
        label = ttk.Label(frame, text=value, style="CardValue.TLabel")
        label.pack(anchor="w", pady=(4, 0))
        return label

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose an inventory file",
            filetypes=[("Inventory files", "*.csv *.xlsx"), ("CSV files", "*.csv"), ("Excel workbooks", "*.xlsx")],
        )
        if not path:
            return
        try:
            self.headers, self.records = load_inventory(path)
        except InventoryError as exc:
            messagebox.showerror("Could not open inventory", str(exc), parent=self)
            return
        except Exception as exc:  # Surface file/parser errors without crashing the UI.
            messagebox.showerror("Could not open inventory", f"Unexpected file error: {exc}", parent=self)
            return
        self.file_label.configure(text=Path(path).name)
        self.selected_path = Path(path)
        self._show_preview()
        blank = sum(not value.strip() for record in self.records for value in record.values())
        self.row_count.configure(text=str(len(self.records)))
        self.column_count.configure(text=str(len(self.headers)))
        self.blank_count.configure(text=str(blank))
        self.status.configure(text=f"Loaded {len(self.records):,} rows from a local file. No data was uploaded.")

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="Choose blueprint output folder", initialdir=str(self.output_path.parent))
        if path:
            self.output_path = Path(path)
            self.output_label.configure(text=str(self.output_path))

    def _refresh_models(self) -> None:
        try:
            models = list_local_models()
        except Exception as exc:
            messagebox.showinfo("Ollama unavailable", f"Could not read local Ollama models at 127.0.0.1:11434.\n\n{exc}", parent=self)
            return
        self.model_entry.configure(values=models)
        if models and not self.model_entry.get().strip():
            self.model_entry.set(models[0])
        if not models:
            messagebox.showinfo("No local models", "Ollama is running, but it reports no installed models.", parent=self)

    def _generate(self) -> None:
        if self.busy:
            return
        if not self.selected_path:
            messagebox.showinfo("Choose an inventory", "Open a CSV or XLSX inventory file first.", parent=self)
            return
        self.busy = True
        self.generate_button.configure(state="disabled")
        model = self.model_entry.get().strip()
        source_path = self.selected_path
        output_path = self.output_path
        model_note = f" and querying local model '{model}'" if model else ""
        self.status.configure(text=f"Analyzing the local inventory{model_note}; no cloud services are used.")
        self.progress.pack(fill="x", pady=(8, 0))
        self.progress.start(12)

        def worker() -> None:
            try:
                result = build_blueprint(source_path, output_path, model)
                self.result_queue.put((True, result))
            except Exception as exc:
                self.result_queue.put((False, exc))

        threading.Thread(target=worker, daemon=True).start()
        self.after(150, self._check_result)

    def _check_result(self) -> None:
        if self.result_queue.empty():
            self.after(150, self._check_result)
            return
        ok, result = self.result_queue.get()
        self.busy = False
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_button.configure(state="normal")
        if not ok:
            self.status.configure(text="Blueprint generation stopped. The local input was not uploaded.")
            messagebox.showerror("Blueprint generation failed", str(result), parent=self)
            return
        files = result
        self.status.configure(text=f"Blueprint saved locally to {self.output_path}")
        messagebox.showinfo("Blueprint ready", "Generated locally:\n\n" + "\n".join(Path(path).name for path in files), parent=self)

    def _show_preview(self) -> None:
        self.table.delete(*self.table.get_children())
        self.table.configure(columns=self.headers)
        for header in self.headers:
            self.table.heading(header, text=header)
            self.table.column(header, width=max(110, min(240, len(header) * 11)), anchor="w")
        for index, record in enumerate(self.records[:100]):
            self.table.insert("", "end", iid=str(index), values=[record.get(header, "") for header in self.headers])


if __name__ == "__main__":
    SmartNetApp().mainloop()
