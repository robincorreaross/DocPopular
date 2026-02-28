"""
result_screen.py - Tela de auditoria humana e resultado.
"""

from __future__ import annotations

import re
import tkinter.messagebox as mb
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import customtkinter as ctk

from core.pdf_generator import gerar_pdf
from core.transaction import Transaction

if TYPE_CHECKING:
    from ui.app import App


class ResultScreen(ctk.CTkFrame):
    def __init__(
        self,
        parent: ctk.CTkFrame,
        app: "App",
        transaction: Transaction,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self.transacao = transaction
        
        self._init_ui()
        self.after(100, self._show_manual_input_form)

    def _init_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=40, pady=(32, 0), sticky="ew")

        ctk.CTkLabel(
            header,
            text="Auditoria Humana",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#E3F2FD",
        ).pack(anchor="w")

        self._header_sub = ctk.CTkLabel(
            header,
            text="Realize a conferência manual dos documentos e insira os dados da transação.",
            font=ctk.CTkFont(size=13),
            text_color="#78909C",
        )
        self._header_sub.pack(anchor="w")

        self.center = ctk.CTkFrame(self, fg_color="#0D1B2A", corner_radius=16)
        self.center.grid(row=1, column=0, padx=40, pady=24, sticky="nsew")
        self.center.grid_columnconfigure(0, weight=1)
        self.center.grid_rowconfigure(0, weight=1)

    def _clear_center(self) -> None:
        for w in self.center.winfo_children():
            w.destroy()

    def _set_subtitle(self, text: str) -> None:
        self._header_sub.configure(text=text)

    def _show_approved(self, autorizacao: str, data: str) -> None:
        self._set_subtitle("Documentação salva com sucesso.")
        self._clear_center()
        
        frame = ctk.CTkFrame(self.center, fg_color="transparent")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(frame, text="✅", font=ctk.CTkFont(size=64)).pack(pady=(0, 8))

        ctk.CTkLabel(
            frame,
            text="Documentação Validada!",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#66BB6A",
        ).pack()

        dados_frame = ctk.CTkFrame(frame, fg_color="#0A2210", corner_radius=10)
        dados_frame.pack(pady=16, ipadx=20, ipady=12)

        ctk.CTkLabel(
            dados_frame,
            text=f"🔖  Autorização: {autorizacao}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#A5D6A7",
        ).pack(padx=24, pady=(8, 2))

        ctk.CTkLabel(
            dados_frame,
            text=f"📅  Data: {data}",
            font=ctk.CTkFont(size=13),
            text_color="#A5D6A7",
        ).pack(padx=24, pady=(2, 8))

        ctk.CTkButton(
            frame,
            text="Nova Transação",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=50,
            width=240,
            corner_radius=10,
            fg_color="#1E3A5F",
            hover_color="#1565C0",
            command=self.app.show_home,
        ).pack(pady=8)

    def _show_manual_input_form(self) -> None:
        """Formulário para preenchimento manual de autorização e data."""
        self._set_subtitle("Preenchimento manual dos dados da transação.")
        self._clear_center()
        
        frame = ctk.CTkFrame(self.center, fg_color="transparent")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            frame,
            text="📝 Entrada Manual",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#4FC3F7",
        ).pack(pady=(0, 20))

        # Autorização
        ctk.CTkLabel(
            frame, 
            text="Número de Autorização (XXX.XXX.XXX.XXX.XXX):", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#A5D6A7"
        ).pack(anchor="w", padx=2)
        
        self.var_auth = ctk.StringVar()
        self.var_auth.trace_add("write", self._aplicar_mascara_auth)
        
        self.entry_auth = ctk.CTkEntry(
            frame, 
            textvariable=self.var_auth,
            placeholder_text="Ex: 111.222.333.444.555", 
            width=320,
            height=38,
            corner_radius=8
        )
        self.entry_auth.pack(pady=(2, 12))

        # Data
        ctk.CTkLabel(
            frame, 
            text="Data da Transação (DD-MM-AAAA):", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#A5D6A7"
        ).pack(anchor="w", padx=2)
        
        self.var_date = ctk.StringVar()
        self.var_date.trace_add("write", self._aplicar_mascara_data)

        self.entry_date = ctk.CTkEntry(
            frame, 
            textvariable=self.var_date,
            placeholder_text="Ex: 24-02-2026", 
            width=320,
            height=38,
            corner_radius=8
        )
        self.entry_date.pack(pady=(2, 20))

        ctk.CTkButton(
            frame,
            text="💾   Gerar e Salvar PDF",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=50,
            width=320,
            fg_color="#2E7D32",
            hover_color="#388E3C",
            command=self._salvar_manual,
        ).pack(pady=8)

        ctk.CTkButton(
            frame,
            text="Voltar e Revisar Imagens",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color="#78909C",
            command=lambda: self.app.show_scan(self.transacao),
        ).pack()

    def _salvar_manual(self) -> None:
        """Valida entradas manuais e gera o PDF."""
        auth = self.var_auth.get().strip()
        date = self.var_date.get().strip()
        
        if not auth or not date:
            mb.showwarning("Campos Vazios", "Por favor, preencha todos os campos para salvar.")
            return

        # Validação de Autorização
        pattern_auth = r"^\d{3}\.\d{3}\.\d{3}\.\d{3}\.\d{3}$"
        if not re.match(pattern_auth, auth):
            mb.showerror(
                "Formato Inválido", 
                "A Autorização deve ter exatamente 15 números (XXX.XXX.XXX.XXX.XXX)."
            )
            return

        # Validação de Data
        pattern_date = r"^\d{2}-\d{2}-\d{4}$"
        if not re.match(pattern_date, date):
            mb.showerror(
                "Formato Inválido", 
                "A Data deve seguir o formato DD-MM-AAAA."
            )
            return

        # Salva PDF
        try:
            out_folder = self.app.settings.get("output_folder")
            images = self.transacao.todas_imagens()
            
            pdf_path = gerar_pdf(
                imagens=images,
                autorizacao=auth,
                data=date,
                output_folder=out_folder
            )
            
            self._show_approved(auth, date)
            
            # Tenta abrir a pasta
            try:
                import os
                if hasattr(os, 'startfile'):
                    os.startfile(pdf_path.parent)
            except Exception:
                pass
            
        except Exception as e:
            mb.showerror("Erro ao Salvar", f"Não foi possível gerar o PDF:\n{e}")

    def _aplicar_mascara_auth(self, *args: object) -> None:
        """Formata a autorização como XXX.XXX.XXX.XXX.XXX preservando o cursor."""
        texto_atual = self.var_auth.get()
        entry_widget = self.entry_auth._entry
        
        try:
            pos_cursor = entry_widget.index("insert")
        except Exception:
            pos_cursor = len(texto_atual)
            
        texto_antes_cursor = texto_atual[:pos_cursor]
        digitos_antes = sum(1 for c in texto_antes_cursor if c.isdigit())
        
        apenas_nums = "".join(filter(str.isdigit, texto_atual))[:15]
        blocos = [apenas_nums[i:i+3] for i in range(0, len(apenas_nums), 3)]
        novo_texto = ".".join(blocos)
        
        if texto_atual != novo_texto:
            self.var_auth.set(novo_texto)
            nova_pos = 0
            digitos_contados = 0
            for i, char in enumerate(novo_texto):
                if digitos_contados >= digitos_antes: break
                if char.isdigit(): digitos_contados = digitos_contados + 1
                nova_pos = i + 1
            entry_widget.after(10, lambda: entry_widget.icursor(nova_pos))

    def _aplicar_mascara_data(self, *args: object) -> None:
        """Formata a data como DD-MM-AAAA preservando o cursor."""
        texto_atual = self.var_date.get()
        entry_widget = self.entry_date._entry
        
        try:
            pos_cursor = entry_widget.index("insert")
        except Exception:
            pos_cursor = len(texto_atual)
            
        texto_antes_cursor = texto_atual[:pos_cursor]
        digitos_antes = sum(1 for c in texto_antes_cursor if c.isdigit())
        
        apenas_nums = "".join(filter(str.isdigit, texto_atual))[:8]
        novo_texto = ""
        if len(apenas_nums) > 0: novo_texto += apenas_nums[:2]
        if len(apenas_nums) > 2: novo_texto += "-" + apenas_nums[2:4]
        if len(apenas_nums) > 4: novo_texto += "-" + apenas_nums[4:8]
            
        if texto_atual != novo_texto:
            self.var_date.set(novo_texto)
            nova_pos = 0
            digitos_contados = 0
            for i, char in enumerate(novo_texto):
                if digitos_contados >= digitos_antes: break
                if char.isdigit(): digitos_contados = digitos_contados + 1
                nova_pos = i + 1
            entry_widget.after(10, lambda: entry_widget.icursor(nova_pos))
