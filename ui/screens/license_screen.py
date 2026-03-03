"""
license_screen.py - Tela de ativação de licença do DocPopular (Apenas Online).
Exibida ao iniciar o app quando não há licença válida on-line ou off-line.
"""

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk
import tkinter.messagebox as mb

from core.license import (
    LicenseError,
    get_machine_id,
    validar_licenca,
)

if TYPE_CHECKING:
    from ui.app import App


class LicenseScreen(ctk.CTk):
    """
    Janela standalone de ativação de licença dinâmica.
    Suporta estados: 'novo', 'expirado', 'inativo' e 'padrao'.
    """

    def __init__(self, settings: dict, on_activate: object, estado: str = "novo", msg_extra: str = "") -> None:
        super().__init__()
        self.settings = settings
        self.on_activate = on_activate
        self.estado = estado.lower()
        self.msg_extra = msg_extra
        self.machine_id = get_machine_id()

        self.title("DocPopular — Gerenciamento de Licença")
        self.geometry("600x580")
        self.resizable(False, False)
        self.configure(fg_color="#0A1628")

        # Centraliza a janela
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 600) // 2
        y = (self.winfo_screenheight() - 580) // 2
        self.geometry(f"600x580+{x}+{y}")

        self._build()

    def _build(self) -> None:
        # Configurações baseadas no estado
        config = {
            "novo": {
                "icon": "👋",
                "titulo": "Seja Bem-vindo!",
                "subtitulo": "Para começar a usar o DocPopular, você precisa de uma licença ativa.",
                "orientacao": "Fale com o administrador para escolher o plano ideal e liberar seu acesso.",
                "cor": "#4FC3F7",
                "zap_msg": f"Olá Robinson, acabei de instalar o DocPopular e gostaria de escolher um plano. Meu ID: {self.machine_id}"
            },
            "expirado": {
                "icon": "⚠️",
                "titulo": "Sua Licença Expirou",
                "subtitulo": "O prazo de validade do seu plano atual chegou ao fim.",
                "orientacao": "Entre em contato para renovar sua assinatura e continuar sua operação.",
                "cor": "#EF5350",
                "zap_msg": f"Olá Robinson, minha licença do DocPopular expirou. Gostaria de renovar. Meu ID: {self.machine_id}"
            },
            "inativo": {
                "icon": "🚫",
                "titulo": "Licença Inativada",
                "subtitulo": "Seu acesso foi desativado temporariamente pelo administrador.",
                "orientacao": "Favor entrar em contato para verificar o status da sua conta.",
                "cor": "#FF9800",
                "zap_msg": f"Olá Robinson, meu acesso ao DocPopular aparece como Inativo. Pode verificar? Meu ID: {self.machine_id}"
            }
        }.get(self.estado, {
            "icon": "💊",
            "titulo": "DocPopular",
            "subtitulo": "Gerenciamento inteligente de licenças.",
            "orientacao": "Entre em contato para ativar sua licença.",
            "cor": "#4FC3F7",
            "zap_msg": f"Olá Robinson, preciso de ativação no DocPopular. Meu ID: {self.machine_id}"
        })

        self.zap_msg = config["zap_msg"]

        # ── Cabeçalho ──────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text=config["icon"], font=ctk.CTkFont(size=50)).pack(pady=(30, 0))
        
        ctk.CTkLabel(
            self,
            text=config["titulo"],
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=config["cor"],
        ).pack(pady=(5, 5))

        ctk.CTkLabel(
            self,
            text=config["subtitulo"],
            font=ctk.CTkFont(size=13),
            text_color="#90A4AE",
            wraplength=500
        ).pack(pady=(0, 20))

        # ── Card Machine ID ───────────────────────────────────────────────────
        mid_frame = ctk.CTkFrame(self, fg_color="#0D1B2A", corner_radius=15, border_width=1, border_color="#1E3A5F")
        mid_frame.pack(padx=60, fill="x")

        ctk.CTkLabel(
            mid_frame,
            text="🖥️  Seu Identificador (Machine ID)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#B0BEC5",
        ).pack(anchor="w", padx=25, pady=(15, 5))

        mid_inner = ctk.CTkFrame(mid_frame, fg_color="#152030", corner_radius=10)
        mid_inner.pack(padx=20, pady=(5, 10), fill="x")

        self._mid_label = ctk.CTkLabel(
            mid_inner,
            text=self.machine_id,
            font=ctk.CTkFont(family="Courier New", size=18, weight="bold"),
            text_color="#E3F2FD",
        )
        self._mid_label.pack(side="left", padx=20, pady=12)

        ctk.CTkButton(
            mid_inner,
            text="📋 Copiar",
            width=90,
            height=32,
            fg_color="#1565C0",
            command=self._copiar_mid,
        ).pack(side="right", padx=15, pady=12)

        ctk.CTkLabel(
            mid_frame,
            text=config["orientacao"],
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#546E7A",
            wraplength=440,
        ).pack(padx=25, pady=(0, 15))

        # ── Botões de Ação ─────────────────────────────────────────────────────
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.pack(padx=60, pady=25, fill="x")

        self.btn_recheck = ctk.CTkButton(
            actions_frame,
            text="🔄  Já adquiri! Verificar Agora",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=48,
            corner_radius=10,
            fg_color="#0D47A1",
            command=self._recheck,
        )
        self.btn_recheck.pack(fill="x", pady=5)

        ctk.CTkButton(
            actions_frame,
            text="💬  Falar com Robinson (WhatsApp)",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=48,
            corner_radius=10,
            fg_color="#2E7D32",
            hover_color="#388E3C",
            command=self._abrir_whatsapp,
        ).pack(fill="x", pady=5)

        # ── Status ─────────────────────────────────────────────────────────────
        self._status_label = ctk.CTkLabel(
            self,
            text=self.msg_extra if self.msg_extra else "Aguardando ativação...",
            font=ctk.CTkFont(size=11),
            text_color="#546E7A",
            wraplength=480,
        )
        self._status_label.pack(padx=60)

    def _copiar_mid(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.machine_id)
        self._status_label.configure(text="✅ ID copiado! Envie pelo WhatsApp.", text_color="#66BB6A")

    def _recheck(self) -> None:
        self._status_label.configure(text="🔍 Verificando no servidor...", text_color="#4FC3F7")
        self.update()
        try:
            info = validar_licenca("")
            if info.get("valido"):
                mb.showinfo("Sucesso", "✅ Acesso liberado! Bom trabalho.")
                self.destroy()
                self.on_activate() # type: ignore[operator]
            else:
                self._status_label.configure(text="❌ Ainda não consta como ativo na planilha.", text_color="#EF5350")
        except LicenseError as e:
            msg = str(e)
            if "novo" in msg: msg = "Aguardando liberação no sistema."
            self._status_label.configure(text=f"❌ {msg}", text_color="#EF5350")
        except Exception:
            self._status_label.configure(text="⚠️ Verifique sua internet.", text_color="#FFA726")

    def _abrir_whatsapp(self) -> None:
        import urllib.parse
        url = f"https://wa.me/5516991080895?text={urllib.parse.quote(self.zap_msg)}"
        webbrowser.open(url)


class LicenseExpiredScreen(LicenseScreen):
    def __init__(self, settings: dict, on_activate: object, msg_extra: str = "") -> None:
        super().__init__(settings, on_activate, estado="expirado", msg_extra=msg_extra)
