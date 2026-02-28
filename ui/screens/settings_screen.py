"""
settings_screen.py - Tela de configurações: Scanner e Armazenamento (DocPopular).
"""

import threading
import customtkinter as ctk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
from pathlib import Path
from core import scanner as scan_module


class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        # Cópia local das configurações para edição
        import copy
        self.settings = copy.deepcopy(app.settings)
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=40, pady=(32, 8), sticky="ew")

        ctk.CTkLabel(
            header,
            text="Configurações",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#E3F2FD",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Gerencie as configurações de scanner e armazenamento do DocPopular.",
            font=ctk.CTkFont(size=13),
            text_color="#78909C",
        ).pack(anchor="w")

        # Separador
        ctk.CTkFrame(self, height=1, fg_color="#1E3450").grid(
            row=0, column=0, sticky="ew", padx=40, pady=(80, 0)
        )

        # ScrollFrame com seções
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=40, pady=8)
        scroll.grid_columnconfigure(0, weight=1)

        self._build_storage_section(scroll)
        self._build_scanner_section(scroll)

        # Botão salvar
        ctk.CTkButton(
            self,
            text="💾   Salvar Configurações",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=46,
            corner_radius=10,
            fg_color="#1565C0",
            hover_color="#1976D2",
            command=self._salvar,
        ).grid(row=2, column=0, padx=40, pady=16)

    # ── Seção Armazenamento ─────────────────────────────────────────────────────

    def _build_storage_section(self, parent):
        section = self._make_section(parent, "📂  Armazenamento")
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(section, text="Pasta de saída dos PDFs:", font=ctk.CTkFont(size=12), text_color="#90A4AE").grid(
            row=0, column=0, sticky="w", padx=4, pady=(4, 2)
        )

        path_row = ctk.CTkFrame(section, fg_color="transparent")
        path_row.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 8))
        path_row.grid_columnconfigure(0, weight=1)

        self.folder_var = ctk.StringVar(value=self.settings.get("output_folder", ""))
        self.folder_entry = ctk.CTkEntry(
            path_row,
            textvariable=self.folder_var,
            font=ctk.CTkFont(size=12),
            height=38,
            state="readonly",
        )
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            path_row,
            text="📂  Alterar",
            width=110,
            height=38,
            fg_color="#1E3A5F",
            hover_color="#1565C0",
            command=self._escolher_pasta,
        ).grid(row=0, column=1)

        # Contagem de PDFs
        self.lbl_count = ctk.CTkLabel(
            section, text="", font=ctk.CTkFont(size=11), text_color="#546E7A"
        )
        self.lbl_count.grid(row=2, column=0, sticky="w", padx=4, pady=(0, 8))
        self._update_pdf_count()

    # ── Seção Scanner ──────────────────────────────────────────────────────────

    def _build_scanner_section(self, parent):
        section = self._make_section(parent, "🖨️  Scanner")
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(section, text="Scanner selecionado:", font=ctk.CTkFont(size=12), text_color="#90A4AE").grid(
            row=0, column=0, sticky="w", padx=4, pady=(4, 2)
        )

        scanner_row = ctk.CTkFrame(section, fg_color="transparent")
        scanner_row.grid(row=1, column=0, sticky="ew", padx=4)
        scanner_row.grid_columnconfigure(0, weight=1)

        self.scanner_list = scan_module.list_scanners()
        scanner_values = self.scanner_list if self.scanner_list else ["(Nenhum scanner detectado)"]

        current_scanner = self.settings.get("scanner_name", "")
        combo_val = current_scanner if current_scanner in self.scanner_list else scanner_values[0]

        self.scanner_var = ctk.StringVar(value=combo_val)
        self.scanner_combo = ctk.CTkComboBox(
            scanner_row,
            variable=self.scanner_var,
            values=scanner_values,
            font=ctk.CTkFont(size=12),
            height=38,
            state="readonly" if not self.scanner_list else "normal",
        )
        self.scanner_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            scanner_row,
            text="🔄  Atualizar",
            width=110,
            height=38,
            fg_color="#1E3A5F",
            hover_color="#1565C0",
            command=self._atualizar_scanners,
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            scanner_row,
            text="🧪  Testar",
            width=90,
            height=38,
            fg_color="#37474F",
            hover_color="#455A64",
            command=self._testar_scanner,
        ).grid(row=0, column=2)

        self.lbl_scanner_status = ctk.CTkLabel(
            section,
            text="ℹ️  Caso nenhum scanner seja detectado, o sistema usará importação de arquivo.",
            font=ctk.CTkFont(size=11),
            text_color="#546E7A",
            wraplength=540,
            justify="left",
        )
        self.lbl_scanner_status.grid(row=2, column=0, sticky="w", padx=4, pady=(8, 8))

    # ── Helpers da UI ──────────────────────────────────────────────────────────

    def _make_section(self, parent, title: str) -> ctk.CTkFrame:
        """Cria uma caixa de seção com título."""
        outer = ctk.CTkFrame(parent, fg_color="#0D1B2A", corner_radius=12)
        outer.pack(fill="x", pady=8)
        outer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            outer,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4FC3F7",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 8))

        ctk.CTkFrame(outer, height=1, fg_color="#1E3450").grid(
            row=1, column=0, sticky="ew", padx=20, pady=(0, 12)
        )

        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 16))
        inner.grid_columnconfigure(0, weight=1)
        return inner

    def _update_pdf_count(self):
        folder = self.settings.get("output_folder", "")
        if folder and Path(folder).exists():
            count = len(list(Path(folder).glob("*.pdf")))
            self.lbl_count.configure(text=f"📄  {count} arquivo(s) PDF salvos nesta pasta.")
        else:
            self.lbl_count.configure(text="⚠️  Pasta não existe ainda (será criada ao salvar o primeiro PDF).")

    def _escolher_pasta(self):
        path = fd.askdirectory(title="Selecionar pasta de saída dos PDFs")
        if path:
            self.folder_var.set(path)
            self.settings["output_folder"] = path
            self._update_pdf_count()

    def _atualizar_scanners(self):
        self.scanner_list = scan_module.list_scanners()
        values = self.scanner_list if self.scanner_list else ["(Nenhum scanner detectado)"]
        self.scanner_combo.configure(values=values)
        self.scanner_var.set(values[0])
        status = f"✅  {len(self.scanner_list)} scanner(s) detectado(s)." if self.scanner_list else "❌  Nenhum scanner encontrado."
        self.lbl_scanner_status.configure(text=status)

    def _testar_scanner(self):
        scanner_name = self.scanner_var.get()
        if not scanner_name or "(Nenhum" in scanner_name:
            mb.showwarning("Scanner", "Nenhum scanner selecionado.")
            return

        self.lbl_scanner_status.configure(text="⌛  Realizando scan de teste...")

        def run():
            img, err = scan_module.scan_page(scanner_name)
            if img:
                self.after(0, lambda: self.lbl_scanner_status.configure(
                    text=f"✅  Scan de teste bem-sucedido! ({img.size[0]}x{img.size[1]} px)",
                    text_color="#66BB6A"
                ))
            else:
                msg = f"❌  Falha no scan: {err}" if err else "❌  Falha no scan de teste. Verifique o scanner."
                self.after(0, lambda: self.lbl_scanner_status.configure(
                    text=msg,
                    text_color="#EF5350"
                ))

        threading.Thread(target=run, daemon=True).start()

    # ── Salvar ──────────────────────────────────────────────────────────────────

    def _salvar(self):
        # Captura valores atuais
        self.settings["output_folder"] = self.folder_var.get()
        scanner_val = self.scanner_var.get()
        self.settings["scanner_name"] = scanner_val if "(Nenhum" not in scanner_val else ""

        self.app.update_settings(self.settings)
        mb.showinfo("Configurações", "Configurações salvas com sucesso!")
