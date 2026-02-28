"""
app.py - Janela principal do DocPopular com navegação por abas laterais.
"""

from __future__ import annotations

from typing import Any, List

import customtkinter as ctk
from core.config import load_settings, save_settings
from version import APP_VERSION


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DocPopular — Auditor de Documentos PFPB")
        self.geometry("1150x720")
        self.minsize(1000, 650)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.settings = load_settings()
        self.current_transaction = None
        self._update_zip_url: str = ""  # URL do ZIP da nova versão (preenchido ao detectar update)
        self._license_cache: dict | None = None  # Cache global para evitar lag na UI (v1.1.7)

        self._build_layout()
        self.show_home()

        # Verificações em background após 1 segundo
        self.after(1000, self._iniciar_verificacao_update)
        self.after(1500, self._verificar_expiracao_proxima)

    # ── Layout ───────────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        """Monta o layout base: sidebar + área de conteúdo."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)  # row 0 = banner de update

        # ── Banner de Alerta de Expiração (Novo v1.1.4) ──────────────────────
        self._expiration_banner = ctk.CTkFrame(self, height=0, fg_color="#FF9800", corner_radius=0)
        self._expiration_banner.grid(row=0, column=0, columnspan=2, sticky="ew")
        self._expiration_banner.grid_remove() # Inicia escondido

        # Banner de atualização (oculto inicialmente)
        self._update_banner = ctk.CTkFrame(self, fg_color="#0D2B0D", height=42, corner_radius=0)
        self._update_banner.grid(row=0, column=0, columnspan=2, sticky="ew")
        self._update_banner.grid_remove()  # oculto até haver update

        # ── Sidebar ──────────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#0D1B2A")
        self.sidebar.grid(row=1, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=16, pady=(24, 8), sticky="ew")

        ctk.CTkLabel(logo_frame, text="🏥", font=ctk.CTkFont(size=32)).pack()
        ctk.CTkLabel(
            logo_frame,
            text="DocPopular",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4FC3F7",
        ).pack()
        ctk.CTkLabel(
            logo_frame,
            text="Auditor PFPB",
            font=ctk.CTkFont(size=10),
            text_color="#78909C",
        ).pack()

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#1E3450").grid(
            row=1, column=0, sticky="ew", padx=16, pady=8
        )

        self.btn_home = ctk.CTkButton(
            self.sidebar,
            text="  📋  Nova Transação",
            font=ctk.CTkFont(size=13),
            anchor="w",
            corner_radius=8,
            fg_color="transparent",
            hover_color="#1E3A5F",
            command=self.show_home,
        )
        self.btn_home.grid(row=2, column=0, padx=12, pady=4, sticky="ew")

        self.btn_settings = ctk.CTkButton(
            self.sidebar,
            text="  ⚙️  Configurações",
            font=ctk.CTkFont(size=13),
            anchor="w",
            corner_radius=8,
            fg_color="transparent",
            hover_color="#1E3A5F",
            command=self.show_settings,
        )
        self.btn_settings.grid(row=5, column=0, padx=12, pady=4, sticky="ew")



        self.btn_search_doc = ctk.CTkButton(
            self.sidebar,
            text="  🔍  Procurar Documento",
            font=ctk.CTkFont(size=13),
            anchor="w",
            corner_radius=8,
            fg_color="transparent",
            hover_color="#1E3A5F",
            command=self.show_search_doc,
        )
        self.btn_search_doc.grid(row=3, column=0, padx=12, pady=4, sticky="ew")

        self.btn_help = ctk.CTkButton(
            self.sidebar,
            text="  ❓  Ajuda e Suporte",
            font=ctk.CTkFont(size=13),
            anchor="w",
            corner_radius=8,
            fg_color="transparent",
            hover_color="#1E3A5F",
            command=self.show_help,
        )
        self.btn_help.grid(row=6, column=0, padx=12, pady=4, sticky="ew")

        # Rodapé com versão
        ctk.CTkLabel(
            self.sidebar,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=10),
            text_color="#B0BEC5",
        ).grid(row=11, column=0, padx=16, pady=12, sticky="sw")

        # ── Área de conteúdo ─────────────────────────────────────────────────
        self.content_frame = ctk.CTkFrame(self, fg_color="#0A1628", corner_radius=0)
        self.content_frame.grid(row=1, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self._current_screen = None

    # ── Sistema de update ────────────────────────────────────────────────────────

    def _verificar_expiracao_proxima(self) -> None:
        """Verifica licença online, alimenta o cache e mostra banner se faltar <= 3 dias."""
        try:
            from core.license import validar_licenca, carregar_licenca
            key = carregar_licenca(self.settings)
            info = validar_licenca(key or "")
            
            # Alimenta o cache global para as telas (v1.1.7)
            self._license_cache = info
            
            dias = info.get("dias_restantes", 999)
            if 0 <= dias <= 3:
                self._mostrar_banner_expiracao(dias)
        except Exception as e:
            print(f"[DEBUG] Falha na verificação de expiração/cache: {e}")

    def _mostrar_banner_expiracao(self, dias: int) -> None:
        """Exibe o banner laranja de aviso de expiração."""
        for w in self._expiration_banner.winfo_children():
            w.destroy()
            
        self._expiration_banner.grid()
        
        msg = f"⚠️ Sua licença expira em {dias} dia(s)! Clique aqui para renovar agora." if dias > 0 else "⚠️ Sua licença expira HOJE! Renove agora para não parar."
        
        btn = ctk.CTkButton(
            self._expiration_banner,
            text=msg,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent",
            hover_color="#E68A00",
            text_color="white",
            anchor="center",
            command=self._abrir_whatsapp_renovacao
        )
        btn.pack(fill="x", ipady=5)

    def _abrir_whatsapp_renovacao(self) -> None:
        import webbrowser
        import urllib.parse
        from core.license import get_machine_id
        mid = get_machine_id()
        msg = f"Olá Robinson, minha licença do DocPopular está vencendo e gostaria de renovar. Meu ID: {mid}"
        url = f"https://wa.me/5516991080895?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def _iniciar_verificacao_update(self) -> None:
        """Dispara a verificação de update em background."""
        try:
            from core.updater import verificar_atualizacao
            verificar_atualizacao(
                on_update_available=lambda v, c, m, z: self.after(
                    0, lambda: self._mostrar_banner_update(v, c, m, z)
                )
            )
        except Exception:
            pass  # Silencioso se o módulo ou rede não estiver disponível

    def _mostrar_banner_update(
        self, nova_versao: str, changelog: List[str], obrigatoria: bool, zip_url: str = ""
    ) -> None:
        """Exibe o banner de notificação de update no topo do app."""
        self._update_zip_url = zip_url  # guarda para uso no download
        # Limpa o banner anterior
        for w in self._update_banner.winfo_children():
            w.destroy()

        # Reaparece o banner
        self._update_banner.grid()

        emoji = "🚨" if obrigatoria else "🟢"
        tipo = "OBRIGATÓRIA" if obrigatoria else "disponível"
        texto = f"{emoji}  Atualização {tipo}: versão {nova_versao}   —   {changelog[0] if changelog else ''}"

        banner_inner = ctk.CTkFrame(self._update_banner, fg_color="transparent")
        banner_inner.pack(fill="x", expand=True, padx=16)

        ctk.CTkLabel(
            banner_inner,
            text=texto,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#A5D6A7" if not obrigatoria else "#FFCDD2",
        ).pack(side="left", pady=8)

        ctk.CTkButton(
            banner_inner,
            text="⬇️  Baixar agora",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28,
            width=120,
            corner_radius=6,
            fg_color="#2E7D32" if not obrigatoria else "#C62828",
            hover_color="#388E3C" if not obrigatoria else "#D32F2F",
            command=self._abrir_download,
        ).pack(side="right", pady=7)

        if not obrigatoria:
            ctk.CTkButton(
                banner_inner,
                text="✕",
                font=ctk.CTkFont(size=11),
                height=28,
                width=28,
                corner_radius=6,
                fg_color="transparent",
                hover_color="#1E3A5F",
                text_color="#78909C",
                command=self._fechar_banner,
            ).pack(side="right", padx=4, pady=7)

    def _abrir_download(self) -> None:
        """Inicia download automático se possível, senão abre browser."""
        if self._update_zip_url:
            self._mostrar_progresso_download(self._update_zip_url)
        else:
            from core.updater import abrir_download
            abrir_download()

    def _mostrar_progresso_download(self, zip_url: str) -> None:
        """Abre janela modal de progresso de download e instala automaticamente."""
        from core.updater import baixar_e_instalar

        dialog = ctk.CTkToplevel(self)
        dialog.title("Instalando Atualização")
        dialog.geometry("480x240")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#0A1628")
        dialog.grab_set()  # modal
        dialog.lift()

        # Centraliza
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 480) // 2
        y = self.winfo_y() + (self.winfo_height() - 240) // 2
        dialog.geometry(f"480x240+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="⬇️  Baixando atualização...",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4FC3F7",
        ).pack(pady=(28, 8))

        status_lbl = ctk.CTkLabel(
            dialog,
            text="Conectando...",
            font=ctk.CTkFont(size=12),
            text_color="#78909C",
        )
        status_lbl.pack()

        prog_bar = ctk.CTkProgressBar(dialog, width=400)
        prog_bar.pack(pady=16)
        prog_bar.set(0)

        pct_lbl = ctk.CTkLabel(
            dialog,
            text="0%",
            font=ctk.CTkFont(size=11),
            text_color="#546E7A",
        )
        pct_lbl.pack()

        def on_progress(pct: int, msg: str) -> None:
            self.after(0, lambda: [
                prog_bar.set(pct / 100),
                status_lbl.configure(text=msg),
                pct_lbl.configure(text=f"{pct}%"),
            ])

        def on_success() -> None:
            self.after(0, lambda: [
                status_lbl.configure(text="✅ Instalação concluída! Reiniciando...", text_color="#66BB6A"),
                pct_lbl.configure(text="100%"),
                self.after(2000, self.destroy),  # fecha o app → bat continua a substituição
            ])

        def on_error(msg: str) -> None:
            import webbrowser as _wb
            from version import DOWNLOAD_URL as _dl

            def _show_error() -> None:
                status_lbl.configure(text=f"❌ Erro: {msg}", text_color="#EF5350")
                ctk.CTkButton(
                    dialog,
                    text="Baixar manualmente",
                    command=lambda: _wb.open(_dl),
                ).pack(pady=8)

            self.after(0, _show_error)

        baixar_e_instalar(
            zip_url=zip_url,
            on_progress=on_progress,
            on_success=on_success,
            on_error=on_error,
        )

    def _fechar_banner(self) -> None:
        self._update_banner.grid_remove()

    # ── Navegação ────────────────────────────────────────────────────────────────

    def _set_active_btn(self, active_btn: ctk.CTkButton) -> None:
        for btn in [self.btn_home, self.btn_search_doc, self.btn_settings, self.btn_help]:
            btn.configure(fg_color="transparent")
        active_btn.configure(fg_color="#1E3A5F")

    def _show_screen(self, screen_class: object, **kwargs: object) -> None:
        if self._current_screen:
            self._current_screen.destroy()  # type: ignore[union-attr]
        self._current_screen = screen_class(self.content_frame, self, **kwargs)  # type: ignore[operator]
        self._current_screen.grid(row=0, column=0, sticky="nsew")  # type: ignore[union-attr]

    def show_home(self) -> None:
        from ui.screens.home_screen import HomeScreen
        self._set_active_btn(self.btn_home)
        self._show_screen(HomeScreen)

    def show_scan(self, transaction: object) -> None:
        from ui.screens.scan_screen import ScanScreen
        self.current_transaction = transaction
        self._show_screen(ScanScreen, transaction=transaction)

    def show_result(self, transaction: object) -> None:
        from ui.screens.result_screen import ResultScreen
        self._show_screen(ResultScreen, transaction=transaction)

    def show_settings(self) -> None:
        from ui.screens.settings_screen import SettingsScreen
        self._set_active_btn(self.btn_settings)
        self._show_screen(SettingsScreen)

    def show_search_doc(self) -> None:
        from ui.screens.search_document_screen import SearchDocumentScreen
        self._set_active_btn(self.btn_search_doc)
        self._show_screen(SearchDocumentScreen)



    def show_help(self) -> None:
        from ui.screens.help_screen import HelpScreen
        self._set_active_btn(self.btn_help)
        self._show_screen(HelpScreen)

    def update_settings(self, new_settings: dict[str, Any]) -> None:
        self.settings = new_settings
        save_settings(new_settings)
