"""
home_screen.py - Tela inicial para seleção do tipo de transação.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import customtkinter as ctk
from core.transaction import TIPOS_TRANSACAO, criar_transacao

if TYPE_CHECKING:
    from ui.app import App


class HomeScreen(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, app: App, **kwargs: object) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self.selected_type: Optional[int] = None
        self.type_buttons: dict[int, tuple[ctk.CTkFrame, ctk.CTkButton]] = {}
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Cabeçalho ─────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=40, pady=(40, 8), sticky="ew")

        ctk.CTkLabel(
            header,
            text="Nova Transação",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#E3F2FD",
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Selecione o tipo de transação para iniciar a digitalização dos documentos.",
            font=ctk.CTkFont(size=13),
            text_color="#78909C",
        ).pack(anchor="w")

        # Separador
        ctk.CTkFrame(self, height=1, fg_color="#1E3450").grid(
            row=1, column=0, sticky="ew", padx=40, pady=(0, 24)
        )

        # ── Cards de tipo ─────────────────────────────────────────────────────
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.grid(row=2, column=0, padx=40, sticky="n")
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        for tipo_id, info in TIPOS_TRANSACAO.items():
            self._build_type_card(cards_frame, tipo_id, info)

        # ── Botão Iniciar ──────────────────────────────────────────────────────
        self.btn_start = ctk.CTkButton(
            self,
            text="▶   Iniciar Digitalização",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color="#1565C0",
            hover_color="#1976D2",
            state="disabled",
            command=self._iniciar,
        )
        self.btn_start.grid(row=3, column=0, padx=40, pady=(40, 40), ipadx=20)

    def _build_type_card(self, parent, tipo_id: int, info: dict):
        col = tipo_id - 1
        card = ctk.CTkFrame(
            parent,
            fg_color="#0D1B2A",
            corner_radius=16,
            border_width=2,
            border_color="#1E3450",
        )
        card.grid(row=0, column=col, padx=12, pady=8, sticky="nsew", ipadx=10, ipady=10)

        ctk.CTkLabel(
            card,
            text=info["icone"],
            font=ctk.CTkFont(size=42),
        ).pack(pady=(24, 8))

        ctk.CTkLabel(
            card,
            text=info["nome"],
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#E3F2FD",
        ).pack()

        ctk.CTkLabel(
            card,
            text=info["descricao"],
            font=ctk.CTkFont(size=11),
            text_color="#78909C",
            wraplength=200,
        ).pack(pady=(4, 8))

        etapas_texto = f"📑 {info['etapas']} etapas de digitalização"
        ctk.CTkLabel(
            card,
            text=etapas_texto,
            font=ctk.CTkFont(size=11),
            text_color="#4FC3F7",
        ).pack(pady=(0, 8))

        btn_select = ctk.CTkButton(
            card,
            text="Selecionar",
            font=ctk.CTkFont(size=12),
            corner_radius=8,
            height=36,
            fg_color="#1E3A5F",
            hover_color="#1565C0",
            command=lambda t=tipo_id, c=card: self._select_type(t, c),
        )
        btn_select.pack(pady=(8, 20), padx=20, fill="x")
        self.type_buttons[tipo_id] = (card, btn_select)

    def _select_type(self, tipo_id: int, card):
        self.selected_type = tipo_id

        # Reset visual de todos os cards
        for tid, (c, b) in self.type_buttons.items():
            c.configure(border_color="#1E3450")
            b.configure(fg_color="#1E3A5F", text="Selecionar")

        # Destaca o selecionado
        card.configure(border_color="#1565C0")
        self.type_buttons[tipo_id][1].configure(fg_color="#1565C0", text="✓ Selecionado")

        # Ativa o botão de iniciar
        self.btn_start.configure(state="normal")

    def _iniciar(self):
        if self.selected_type is None:
            return
        transaction = criar_transacao(self.selected_type)
        self.app.show_scan(transaction)
