"""
search_document_screen.py - Tela de pesquisa avulsa para encontrar documentos na pasta CPFs (Validação + Download).
"""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING, List
from tkinter import filedialog
import tkinter.messagebox as mb
import customtkinter as ctk
from PIL import Image

from core.cpf_manager import find_all_documents_by_cpf, validate_cpf

if TYPE_CHECKING:
    from ui.app import App


class SearchDocumentScreen(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, app: App, **kwargs: object) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._img_refs = []  # Lista para segurar referências de CTkImage e evitar GC
        self._found_paths = [] # Guardo os paths do último CPF buscado
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Cabeçalho ─────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=40, pady=(32, 24), sticky="ew")

        ctk.CTkLabel(
            header,
            text="🔍  Procurar Documento",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#E3F2FD",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Busque por documentos de identificação já digitalizados no sistema informando o CPF.",
            font=ctk.CTkFont(size=14),
            text_color="#78909C",
        ).pack(anchor="w", pady=(4, 0))

        # ── Barra de Busca ────────────────────────────────────────────────────
        search_frame = ctk.CTkFrame(self, fg_color="#0D1B2A", corner_radius=12)
        search_frame.grid(row=1, column=0, padx=40, pady=8, sticky="ew")

        input_container = ctk.CTkFrame(search_frame, fg_color="transparent")
        input_container.pack(pady=24, padx=24)

        ctk.CTkLabel(
            input_container,
            text="CPF:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#A5D6A7",
        ).pack(side="left", padx=(0, 12))

        self.var_cpf = ctk.StringVar()
        self.var_cpf.trace_add("write", self._aplicar_mascara_cpf)

        self.entry_cpf = ctk.CTkEntry(
            input_container,
            textvariable=self.var_cpf,
            placeholder_text="000.000.000-00",
            width=220,
            height=40,
            font=ctk.CTkFont(size=16),
            corner_radius=8,
        )
        self.entry_cpf.pack(side="left")

        self.lbl_cpf_error = ctk.CTkLabel(
            input_container,
            text="⚠️ CPF Inválido",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FF5252",
        )
        # pack/forget controlado no _aplicar_mascara_cpf

        self.btn_search = ctk.CTkButton(
            input_container,
            text="Pesquisar",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            fg_color="#1E3A5F",
            hover_color="#1565C0",
            command=self._do_search,
        )
        self.btn_search.pack(side="left", padx=16)

        # ── Área de Resultados ────────────────────────────────────────────────
        self.result_frame = ctk.CTkFrame(self, fg_color="#0A1628", corner_radius=12)
        self.result_frame.grid(row=2, column=0, padx=40, pady=(8, 32), sticky="nsew")
        self.result_frame.grid_columnconfigure(0, weight=1)
        self.result_frame.grid_rowconfigure(0, weight=1)

        self._show_empty_state("Digite um CPF válido e clique em Pesquisar.")

    def _show_empty_state(self, message: str) -> None:
        self._img_refs = []
        self._found_paths = []
        for w in self.result_frame.winfo_children():
            w.destroy()
        
        container = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(
            container,
            text="📁",
            font=ctk.CTkFont(size=48)
        ).pack(pady=8)
        
        ctk.CTkLabel(
            container,
            text=message,
            font=ctk.CTkFont(size=14),
            text_color="#546E7A"
        ).pack()

    def _do_search(self) -> None:
        cpf = self.var_cpf.get()
        if len(cpf) != 14:
            self._show_empty_state("CPF incompleto. Formato: XXX.XXX.XXX-XX")
            return
            
        if not validate_cpf(cpf):
            self._show_empty_state("CPF numericamente inválido. Verifique os dígitos.")
            return
            
        file_paths = find_all_documents_by_cpf(cpf, self.app.settings)
        if file_paths:
            self._found_paths = [str(p) for p in file_paths]
            self._show_result(cpf, self._found_paths)
        else:
            self._show_empty_state(f"Nenhum documento encontrado para o CPF {cpf}.")

    def _show_result(self, cpf: str, image_paths: List[str]) -> None:
        self._img_refs = []
        for w in self.result_frame.winfo_children():
            w.destroy()
            
        # Topo dos resultados: Info + Botão Download
        top_bar = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=24, pady=24)
        
        info_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        info_frame.pack(side="left")
        
        ctk.CTkLabel(
            info_frame,
            text="✅ Documento Encontrado!",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#66BB6A",
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            info_frame,
            text=f"Total: {len(image_paths)} página(s) para o CPF {cpf}",
            font=ctk.CTkFont(size=14),
            text_color="#A5D6A7",
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkButton(
            top_bar,
            text="📥  Baixar Documento",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            fg_color="#2E7D32",
            hover_color="#388E3C",
            command=self._download_files,
        ).pack(side="right")

        # Container para imagens
        scroll_frame = ctk.CTkScrollableFrame(self.result_frame, fg_color="#0D1B2A", corner_radius=12)
        scroll_frame.pack(padx=24, pady=(0, 24), fill="both", expand=True)
        
        for i, path in enumerate(image_paths, 1):
            page_label = ctk.CTkLabel(
                scroll_frame, 
                text=f"Página {i}", 
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#78909C"
            )
            page_label.pack(pady=(12, 4))
            
            img_container = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            img_container.pack(pady=(0, 12))
            
            try:
                img = Image.open(path)
                orig_w, orig_h = img.size
                
                # Tamanho do preview no scroll
                target_w = 700
                ratio = target_w / orig_w
                target_h = int(orig_h * ratio)
                
                # Novo objeto ctk.CTkImage preservando nitidez
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(target_w, target_h))
                self._img_refs.append(ctk_img)
                
                lbl_preview = ctk.CTkLabel(img_container, image=ctk_img, text="")
                lbl_preview.pack(padx=16, pady=8)
            except Exception as e:
                ctk.CTkLabel(img_container, text=f"Erro ao carregar página {i}:\n{e}").pack()

    def _download_files(self) -> None:
        """Permite que o usuário salve os arquivos em um local escolhido."""
        if not self._found_paths:
            return
            
        if len(self._found_paths) == 1:
            # Salvar como um arquivo único
            source = self._found_paths[0]
            ext = os.path.splitext(source)[1]
            dest = filedialog.asksaveasfilename(
                title="Salvar Documento",
                defaultextension=ext,
                filetypes=[("Imagens JPEG", "*.jpg")],
                initialfile=os.path.basename(source)
            )
            if dest:
                try:
                    shutil.copy2(source, dest)
                    mb.showinfo("Sucesso", "Documento salvo com sucesso!")
                except Exception as e:
                    mb.showerror("Erro", f"Falha ao salvar arquivo:\n{e}")
        else:
            # Se for múltiplo, salvar em uma pasta
            dest_dir = filedialog.askdirectory(title="Selecione a pasta para salvar as páginas")
            if dest_dir:
                try:
                    for p in self._found_paths:
                        shutil.copy2(p, os.path.join(dest_dir, os.path.basename(p)))
                    mb.showinfo("Sucesso", f"{len(self._found_paths)} páginas salvas com sucesso em:\n{dest_dir}")
                except Exception as e:
                    mb.showerror("Erro", f"Falha ao salvar arquivos:\n{e}")

    def _aplicar_mascara_cpf(self, *args: object) -> None:
        """Aplica a máscara XXX.XXX.XXX-XX."""
        texto_atual = self.var_cpf.get()
        entry_widget = self.entry_cpf._entry
        
        try:
            pos_cursor = entry_widget.index("insert")
        except Exception:
            pos_cursor = len(texto_atual)
            
        texto_antes_cursor = texto_atual[:pos_cursor]
        digitos_antes = sum(1 for c in texto_antes_cursor if c.isdigit())
        
        apenas_nums = "".join(filter(str.isdigit, texto_atual))[:11]
        
        novo_texto = ""
        for i, digito in enumerate(apenas_nums):
            if i in [3, 6]:
                novo_texto += "."
            elif i == 9:
                novo_texto += "-"
            novo_texto += digito
            
        if texto_atual != novo_texto:
            self.var_cpf.set(novo_texto)
            
            nova_pos = 0
            digitos_contados = 0
            for i, char in enumerate(novo_texto):
                if digitos_contados >= digitos_antes:
                    break
                if char.isdigit():
                    digitos_contados += 1
                nova_pos = i + 1
                
            
            entry_widget.after(10, lambda: entry_widget.icursor(nova_pos))

        # Feedback visual imediato
        if len(novo_texto) == 14:
            if validate_cpf(novo_texto):
                self.lbl_cpf_error.pack_forget()
            else:
                self.lbl_cpf_error.pack(side="left", padx=12)
        else:
            self.lbl_cpf_error.pack_forget()
