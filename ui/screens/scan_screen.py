"""
scan_screen.py - Tela de digitalização com navegação por etapas.
"""

import threading
import customtkinter as ctk
from PIL import Image, ImageTk
import re
import tkinter.messagebox as mb
from core import scanner as scan_module
from core.transaction import Transaction
from core.cpf_manager import find_all_documents_by_cpf, save_cpf_documents, validate_cpf


THUMB_SIZE = (120, 120)


class ScanScreen(ctk.CTkFrame):
    def __init__(self, parent, app, transaction: Transaction, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self.transaction = transaction
        self._build()
        self._refresh()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Cabeçalho ─────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=40, pady=(32, 4), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self.lbl_tipo = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#4FC3F7",
        )
        self.lbl_tipo.grid(row=0, column=0, sticky="w")

        self.lbl_titulo = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#E3F2FD",
        )
        self.lbl_titulo.grid(row=1, column=0, sticky="w")

        self.lbl_desc = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="#78909C",
            wraplength=700,
            justify="left",
        )
        self.lbl_desc.grid(row=2, column=0, sticky="w", pady=(4, 0))

        self.lbl_desc.grid(row=2, column=0, sticky="w", pady=(4, 0))

        # ── Campo CPF (Oculto por Padrão) ─────────────────────────────────────
        self.cpf_frame = ctk.CTkFrame(header, fg_color="transparent")
        self.cpf_frame.grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.cpf_frame.grid_remove() # Oculto até precisar

        ctk.CTkLabel(
            self.cpf_frame,
            text="Digite o CPF para continuar:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#A5D6A7",
        ).pack(side="left", padx=(0, 12))

        self.var_cpf = ctk.StringVar()
        self.var_cpf.trace_add("write", self._aplicar_mascara_cpf)

        self.entry_cpf = ctk.CTkEntry(
            self.cpf_frame,
            textvariable=self.var_cpf,
            placeholder_text="000.000.000-00",
            width=160,
            height=32,
            font=ctk.CTkFont(size=14),
            corner_radius=6,
        )
        self.entry_cpf.pack(side="left")

        self.lbl_cpf_error = ctk.CTkLabel(
            self.cpf_frame,
            text="⚠️ CPF Inválido",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FF5252",
        )
        # O pack_forget() ou pack() será controlado no _valida_estado_botoes

        # ── Barra de progresso ────────────────────────────────────────────────
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_frame.grid(row=1, column=0, padx=40, pady=12, sticky="ew")
        prog_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(prog_frame, height=8, corner_radius=4)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.progress_bar.set(0)

        self.lbl_progress = ctk.CTkLabel(
            prog_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#546E7A",
        )
        self.lbl_progress.grid(row=1, column=0, sticky="e")

        # ── Área de thumbs ────────────────────────────────────────────────────
        thumb_container = ctk.CTkFrame(self, fg_color="#0D1B2A", corner_radius=12)
        thumb_container.grid(row=2, column=0, padx=40, pady=8, sticky="nsew")
        thumb_container.grid_columnconfigure(0, weight=1)
        thumb_container.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            thumb_container,
            text="Páginas digitalizadas:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#90A4AE",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        self.thumb_scroll = ctk.CTkScrollableFrame(
            thumb_container,
            fg_color="transparent",
            orientation="horizontal",
            height=170,
        )
        self.thumb_scroll.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 12))

        self.lbl_empty = ctk.CTkLabel(
            self.thumb_scroll,
            text="Nenhuma página digitalizada ainda.",
            font=ctk.CTkFont(size=12),
            text_color="#37474F",
        )
        self.lbl_empty.pack(pady=30)

        # ── Controles ─────────────────────────────────────────────────────────
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=3, column=0, padx=40, pady=16, sticky="ew")
        controls.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_scan = ctk.CTkButton(
            controls,
            text="📷   Escanear Página",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=44,
            corner_radius=10,
            fg_color="#1565C0",
            hover_color="#1976D2",
            command=self._do_scan,
        )
        self.btn_scan.grid(row=0, column=0, padx=8, sticky="ew")

        self.btn_import = ctk.CTkButton(
            controls,
            text="📁   Importar Arquivo",
            font=ctk.CTkFont(size=13),
            height=44,
            corner_radius=10,
            fg_color="#1E3A5F",
            hover_color="#263F6A",
            command=self._do_import,
        )
        self.btn_import.grid(row=0, column=1, padx=8, sticky="ew")

        self.btn_next = ctk.CTkButton(
            controls,
            text="Próxima Etapa  ▶",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=44,
            corner_radius=10,
            fg_color="#2E7D32",
            hover_color="#388E3C",
            state="disabled",
            command=self._pergunta_mais_paginas,
        )
        self.btn_next.grid(row=0, column=2, padx=8, sticky="ew")

        self._thumb_refs = []  # evita garbage collection das imagens

    # ── Atualização do estado visual ──────────────────────────────────────────

    def _refresh(self):
        """Atualiza a UI com o estado atual da etapa."""
        t = self.transaction
        etapa = t.etapa_atual

        self.lbl_tipo.configure(
            text=f"🏥  {t.nome_tipo}  •  Etapa {t.etapa_atual_index + 1} de {t.total_etapas}"
        )
        self.lbl_titulo.configure(text=f"{etapa.icone}  {etapa.titulo}")
        self.lbl_desc.configure(text=etapa.descricao)

        progresso = (t.etapa_atual_index) / t.total_etapas
        self.progress_bar.set(progresso)
        self.lbl_progress.configure(text=f"Etapa {t.etapa_atual_index + 1} / {t.total_etapas}")

        # Lógica do Campo CPF
        if etapa.require_cpf:
            self.cpf_frame.grid()
            # Restaura o CPF caso já tenha sido digitado nesta etapa (ao voltar)
            if etapa.cpf and self.var_cpf.get() != etapa.cpf:
                self.var_cpf.set(etapa.cpf)
        else:
            self.cpf_frame.grid_remove()

        self._render_thumbs(etapa.imagens)
        self._valida_estado_botoes()

    def _valida_estado_botoes(self):
        """Habilita ou desabilita botões de scan e avanço com base na exigência do CPF e imagens."""
        etapa = self.transaction.etapa_atual
        cpf_valido = True
        mostra_erro = False
        
        if etapa.require_cpf:
            cpf_texto = self.var_cpf.get()
            # Valida máscara (14 chars) E algoritmo
            is_completo = len(cpf_texto) == 14
            is_algoritmo_ok = validate_cpf(cpf_texto)
            cpf_valido = is_completo and is_algoritmo_ok
            
            # Mostra erro apenas se estiver completo mas for inválido
            if is_completo and not is_algoritmo_ok:
                mostra_erro = True

        # Controle visual do label de erro
        if mostra_erro:
            self.lbl_cpf_error.pack(side="left", padx=12)
        else:
            self.lbl_cpf_error.pack_forget()

        if cpf_valido:
            self.btn_scan.configure(state="normal")
            self.btn_import.configure(state="normal")
            self.btn_next.configure(state="normal" if etapa.tem_imagens else "disabled")
        else:
            self.btn_scan.configure(state="disabled")
            self.btn_import.configure(state="disabled")
            self.btn_next.configure(state="disabled")

    def _render_thumbs(self, imagens):
        """Renderiza miniaturas das imagens atuais."""
        for widget in self.thumb_scroll.winfo_children():
            widget.destroy()
        self._thumb_refs.clear()

        if not imagens:
            self.lbl_empty = ctk.CTkLabel(
                self.thumb_scroll,
                text="Nenhuma página digitalizada ainda.",
                font=ctk.CTkFont(size=12),
                text_color="#37474F",
            )
            self.lbl_empty.pack(pady=30)
            return

        for i, img in enumerate(imagens):
            frame = ctk.CTkFrame(
                self.thumb_scroll,
                fg_color="#0D2137",
                corner_radius=8,
                border_width=1,
                border_color="#1E3450",
            )
            frame.pack(side="left", padx=6, pady=4)

            # Gera miniatura com CTkImage (HighDPI)
            thumb_img = img.copy()
            thumb_img.thumbnail(THUMB_SIZE, Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=thumb_img, dark_image=thumb_img, size=THUMB_SIZE)
            self._thumb_refs.append(ctk_img)

            lbl_img = ctk.CTkLabel(frame, image=ctk_img, text="")
            lbl_img.pack(padx=6, pady=(6, 2))

            ctk.CTkLabel(
                frame,
                text=f"Pág. {i + 1}",
                font=ctk.CTkFont(size=10),
                text_color="#546E7A",
            ).pack(pady=(0, 2))

            # Botão remover
            ctk.CTkButton(
                frame,
                text="✕",
                width=24,
                height=20,
                font=ctk.CTkFont(size=10),
                fg_color="#B71C1C",
                hover_color="#C62828",
                corner_radius=4,
                command=lambda idx=i: self._remover_imagem(idx),
            ).pack(pady=(0, 6))

    # ── Ações ──────────────────────────────────────────────────────────────────

    def _do_scan(self):
        settings = self.app.settings
        scanner_name = settings.get("scanner_name", "")
        self.btn_scan.configure(state="disabled", text="⌛  Escaneando...")

        def run():
            img = None
            if scanner_name:
                img, err = scan_module.scan_page(scanner_name)
                if err:
                    print(f"[ScanScreen] Falha no scan direto: {err}. Tentando diálogo...")
            
            if img is None:
                img = scan_module.scan_with_dialog()
            
            self.after(0, lambda: self._on_image_captured(img))

        threading.Thread(target=run, daemon=True).start()

    def _do_import(self):
        img = scan_module.import_from_file(self)
        self._on_image_captured(img)

    def _on_image_captured(self, img):
        self.btn_scan.configure(state="normal", text="📷   Escanear Página")
        if img:
            img = scan_module.optimize_image(img)
            self.transaction.etapa_atual.adicionar_imagem(img)
            # Ao adicionar a imagem, se precisou de CPF, a imagem principal será salva 
            # na hora de avançar a etapa
            self._valida_estado_botoes()
            self._refresh()

    def _remover_imagem(self, index: int):
        self.transaction.etapa_atual.remover_imagem(index)
        self._valida_estado_botoes()
        self._refresh()

    def _pergunta_mais_paginas(self):
        """Abre diálogo perguntando se há mais páginas."""
        # Se exige CPF, garanta que foi preenchido e já salva o documento na pasta CPFs
        etapa = self.transaction.etapa_atual
        if etapa.require_cpf:
            cpf_salvo = self.var_cpf.get()
            etapa.cpf = cpf_salvo
            try:
                # Salva TODAS as imagens dessa etapa como o documento de identificação
                if etapa.tem_imagens:
                    save_cpf_documents(cpf_salvo, etapa.imagens, self.app.settings)
            except Exception as e:
                print(f"[ScanScreen] Falha ao salvar doc na pasta CPFs: {e}")

        dialog = _MorePagesDialog(self, self.transaction.etapa_atual.titulo)
        self.wait_window(dialog)
        if dialog.result == "next":
            self._avancar_etapa()
            
    def _avancar_etapa(self):
        # Limpar o campo de CPF no UI para a próxima etapa não reusar o texto
        self.var_cpf.set("")
        
        tem_proxima = self.transaction.avancar_etapa()
        if tem_proxima:
            self._refresh()
        else:
            # Digitalização concluída → auditoria
            self.app.show_result(self.transaction)
            
    # ── Lógica CPF e Máscara ──────────────────────────────────────────────────
    
    def _aplicar_mascara_cpf(self, *args: object) -> None:
        """Aplica a máscara XXX.XXX.XXX-XX e reage quando completo."""
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
            
        # Reavalia estado dos botões (libera scan se tem 14 chars e é válido)
        self._valida_estado_botoes()
        
        # Se acabou de completar 14 caracteres e é válido, testa se existe e alerta o usuário
        if len(novo_texto) == 14 and validate_cpf(novo_texto) and getattr(self, "_last_cpf_check", "") != novo_texto:
            self._last_cpf_check = novo_texto
            self._verificar_documento_existente(novo_texto)

    def _verificar_documento_existente(self, cpf: str) -> None:
        """Verifica se já existem arquivos na pasta CPFs, e exibe o popup."""
        paths_existentes = find_all_documents_by_cpf(cpf, self.app.settings)
        if paths_existentes:
            # Mostra preview (usa a primeira página para o preview do diálogo)
            dialog = _FoundDocumentDialog(self, cpf, str(paths_existentes[0]))
            self.wait_window(dialog)
            if dialog.result == "use":
                # Carregar o arquivo existente
                try:
                    for p in paths_existentes:
                        img = Image.open(p)
                        self.transaction.etapa_atual.adicionar_imagem(img.copy())
                    self._valida_estado_botoes()
                    self._refresh()
                except Exception as e:
                    mb.showerror("Erro", f"Não foi possível carregar o arquivo:\n{e}")
            # Se for "new", apenas faz nada (deixa a lista de imagens vazia para escanear/importar novo)


# ── Diálogo "Mais páginas?" ───────────────────────────────────────────────────

class _MorePagesDialog(ctk.CTkToplevel):
    def __init__(self, parent, etapa_titulo: str):
        super().__init__(parent)
        self.result = None
        self.title("")
        self.geometry("420x200")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus()

        # Centraliza
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - 210
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 100
        self.geometry(f"+{px}+{py}")

        ctk.CTkLabel(
            self,
            text="Mais páginas?",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#E3F2FD",
        ).pack(pady=(24, 4))

        ctk.CTkLabel(
            self,
            text=f"Existem mais páginas para «{etapa_titulo}»?",
            font=ctk.CTkFont(size=12),
            text_color="#78909C",
            wraplength=360,
        ).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(
            btn_frame,
            text="✔   Sim, há mais páginas",
            width=170,
            fg_color="#1E3A5F",
            hover_color="#1565C0",
            command=self._sim,
        ).grid(row=0, column=0, padx=8)

        ctk.CTkButton(
            btn_frame,
            text="▶   Não, próxima etapa",
            width=170,
            fg_color="#2E7D32",
            hover_color="#388E3C",
            command=self._nao,
        ).grid(row=0, column=1, padx=8)

    def _sim(self):
        self.result = "more"
        self.destroy()

    def _nao(self):
        self.result = "next"
        self.destroy()

# ── Diálogo "Documento Encontrado" ───────────────────────────────────────────

class _FoundDocumentDialog(ctk.CTkToplevel):
    """Exibe um aviso informando que o documento já existe, 
    uma pré-visualização, e pergunta se deseja reaproveitar ou substituir."""
    
    def __init__(self, parent, cpf: str, image_path: str):
        super().__init__(parent)
        self.result = "new"  # default
        self.title("Documento Encontrado")
        self.geometry("480x580")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus()

        # Centraliza
        self.update_idletasks()
        width, height = 480, 580
        px = parent.winfo_rootx() + parent.winfo_width() // 2 - width // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - height // 2
        self.geometry(f"{width}x{height}+{px}+{py}")

        ctk.CTkLabel(
            self,
            text="Documento Já Existe",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#4FC3F7",
        ).pack(pady=(24, 8))

        ctk.CTkLabel(
            self,
            text=f"Foi encontrado um documento de identificação salvo para o CPF {cpf}.",
            font=ctk.CTkFont(size=13),
            text_color="#90A4AE",
            wraplength=420,
        ).pack(pady=(0, 20))
        
        # Preview do documento
        preview_frame = ctk.CTkFrame(self, fg_color="#0D1B2A", corner_radius=12)
        preview_frame.pack(padx=32, pady=0, fill="both", expand=True)
        
        try:
            img = Image.open(image_path)
            orig_w, orig_h = img.size
            # Aumentamos o limite do preview para aproveitar o espaço novo
            ratio = min(380/orig_w, 280/orig_h)
            new_size = (int(orig_w * ratio), int(orig_h * ratio))
            
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=new_size)
            self._img_ref = ctk_img
            
            lbl_preview = ctk.CTkLabel(preview_frame, image=ctk_img, text="")
            lbl_preview.pack(expand=True, padx=10, pady=10)
        except Exception:
            ctk.CTkLabel(preview_frame, text="Não foi possível carregar a prévia.").pack(expand=True)

        ctk.CTkLabel(
            self,
            text="O que deseja fazer?",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#E3F2FD",
        ).pack(pady=(20, 16))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 32))

        ctk.CTkButton(
            btn_frame,
            text="📄  Usar Recente Salvo",
            width=200,
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1E3A5F",
            hover_color="#1565C0",
            command=self._use,
        ).grid(row=0, column=0, padx=10)

        ctk.CTkButton(
            btn_frame,
            text="📸  Fazer Nova e Substituir",
            width=200,
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2E7D32",
            hover_color="#388E3C",
            command=self._new,
        ).grid(row=0, column=1, padx=10)

    def _use(self):
        self.result = "use"
        self.destroy()

    def _new(self):
        self.result = "new"
        self.destroy()
