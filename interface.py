import flet as ft
import requests
import os
import threading

URL_BASE = "https://controle-guias.onrender.com"
PASTA_UPLOADS = "uploads_temporarios"
os.makedirs(PASTA_UPLOADS, exist_ok=True)

def main(page: ft.Page):
    # ==========================================
    # 1. CONFIGURAÇÕES DA PÁGINA
    # ==========================================
    page.title = "Controle de Guias de Recebimento"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 450
    page.window_height = 800
    page.padding = 0

    caminho_pdf_selecionado = [None]

    # TEXTO DE STATUS DENTRO DA JANELA BRANCA (Impossível de não ver!)
    texto_status = ft.Text("", color=ft.colors.RED, weight=ft.FontWeight.BOLD, size=12)

    # ==========================================
    # 2. SELETORES DE ARQUIVOS
    # ==========================================
    seletor_nova_guia = ft.FilePicker()
    seletor_assinatura = ft.FilePicker()

    def ao_selecionar_nova_guia(e: ft.FilePickerResultEvent):
        try:
            if e.files and len(e.files) > 0:
                nome_arquivo = e.files[0].name
                caminho_pdf_selecionado[0] = os.path.join(PASTA_UPLOADS, nome_arquivo)
                
                botao_anexar.text = f"PDF: {nome_arquivo}"
                texto_status.value = "PDF escolhido! A enviar para a nuvem..."
                texto_status.color = ft.colors.BLUE
                page.update() 
                
                seletor_nova_guia.upload([
                    ft.FilePickerUploadFile(nome_arquivo, upload_url=page.get_upload_url(nome_arquivo, 60))
                ])
                
                texto_status.value = "PDF pronto! Pode clicar em Salvar."
                texto_status.color = ft.colors.GREEN
                page.update()
        except Exception as erro:
            texto_status.value = f"Erro ao anexar: {erro}"
            texto_status.color = ft.colors.RED
            page.update()

    seletor_nova_guia.on_result = ao_selecionar_nova_guia
    page.overlay.append(seletor_nova_guia)
    page.overlay.append(seletor_assinatura)

    # ==========================================
    # 3. JANELA DE CADASTRAR NOVA GUIA
    # ==========================================
    campo_material = ft.TextField(label="Nome do Material", width=300)
    campo_data = ft.TextField(label="Data de Recebimento", width=300)
    
    botao_anexar = ft.FilledButton("Anexar PDF Inicial", icon=ft.icons.UPLOAD_FILE, on_click=lambda _: seletor_nova_guia.pick_files())

    def salvar_guia(e):
        print("----> Botão Salvar foi clicado!") # Vai aparecer nos logs do Render
        
        if not caminho_pdf_selecionado[0]:
            texto_status.value = "ERRO: Por favor, anexe o PDF primeiro!"
            texto_status.color = ft.colors.RED
            page.update()
            return
            
        if not os.path.exists(caminho_pdf_selecionado[0]):
            texto_status.value = "O PDF ainda não chegou à nuvem. Aguarde 3s e clique de novo."
            texto_status.color = ft.colors.ORANGE
            page.update()
            return

        nome_mat = campo_material.value
        data_rec = campo_data.value

        # Muda o botão e o aviso IMEDIATAMENTE
        botao_salvar.text = "Enviando..."
        botao_salvar.disabled = True
        texto_status.value = "A contactar a API... Por favor aguarde."
        texto_status.color = ft.colors.BLUE
        page.update()

        def enviar_dados_nos_bastidores():
            url_api = f"{URL_BASE}/guias/upload"
            dados = {"nome_material": nome_mat, "data_recebimento": data_rec}
            
            try:
                with open(caminho_pdf_selecionado[0], "rb") as f:
                    arquivos = {"ficheiro_pdf": f}
                    print("----> A enviar para a API...")
                    resposta = requests.post(url_api, data=dados, files=arquivos, timeout=25)
                    print(f"----> API respondeu com status: {resposta.status_code}")
                
                if resposta.status_code == 200:
                    campo_material.value = ""
                    campo_data.value = ""
                    botao_anexar.text = "Anexar PDF Inicial"
                    caminho_pdf_selecionado[0] = None
                    dialogo_nova_guia.open = False
                    texto_status.value = ""
                    carregar_guias() 
                else:
                    texto_status.value = f"A API devolveu erro: {resposta.text}"
                    texto_status.color = ft.colors.RED
                    
            except requests.exceptions.Timeout:
                texto_status.value = "A API demorou a responder (está a acordar). Salve de novo!"
                texto_status.color = ft.colors.ORANGE
                print("----> Timeout na API!")
            except Exception as ex:
                texto_status.value = f"Erro Fatal: {ex}"
                texto_status.color = ft.colors.RED
                print(f"----> ERRO FATAL: {ex}")
            finally:
                botao_salvar.text = "Salvar"
                botao_salvar.disabled = False
                page.update()

        threading.Thread(target=enviar_dados_nos_bastidores).start()

    botao_salvar = ft.FilledButton("Salvar", on_click=salvar_guia, style=ft.ButtonStyle(bgcolor=ft.colors.GREEN, color=ft.colors.WHITE))

    dialogo_nova_guia = ft.AlertDialog(
        title=ft.Text("Cadastrar Novo Material"),
        content=ft.Column([campo_material, campo_data, botao_anexar, texto_status], tight=True), # Texto de status adicionado aqui!
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: setattr(dialogo_nova_guia, 'open', False) or page.update()),
            botao_salvar
        ]
    )
    page.overlay.append(dialogo_nova_guia)

    page.floating_action_button = ft.FloatingActionButton(
        content=ft.Row([ft.Icon(ft.icons.ADD), ft.Text("Nova Guia", color=ft.colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER, tight=True),
        bgcolor=ft.colors.BLUE_ACCENT, width=130,
        on_click=lambda e: setattr(dialogo_nova_guia, 'open', True) or page.update()
    )

    # ==========================================
    # 4. LISTAS VISUAIS DINÂMICAS E ATUALIZAÇÃO
    # ==========================================
    aba_pendentes = ft.ListView(expand=True, controls=[])
    aba_assinadas = ft.ListView(expand=True, controls=[])

    def carregar_guias():
        aba_pendentes.controls.clear()
        aba_assinadas.controls.clear()
        
        try:
            resp_pendentes = requests.get(f"{URL_BASE}/guias/pendentes", timeout=10)
            if resp_pendentes.status_code == 200:
                for guia in resp_pendentes.json().get("guias", []):
                    material = guia.get("nome_material", "Sem Nome")
                    data = guia.get("data_recebimento", "Sem Data")
                    
                    cartao = ft.Card(
                        elevation=3,
                        content=ft.ListTile(
                            leading=ft.Icon(ft.icons.PICTURE_AS_PDF, color=ft.colors.RED_ACCENT, size=40),
                            title=ft.Text(f"Material: {material}", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"Recebido em: {data}\nStatus: Pendente Assinatura"),
                            trailing=ft.FilledButton(
                                "Assinar", icon=ft.icons.EDIT, color=ft.colors.WHITE, bgcolor=ft.colors.ORANGE_ACCENT, 
                                on_click=lambda e: print("Ação assinar em breve")
                            )
                        )
                    )
                    aba_pendentes.controls.append(cartao)

            resp_assinadas = requests.get(f"{URL_BASE}/guias/assinadas", timeout=10)
            if resp_assinadas.status_code == 200:
                for guia in resp_assinadas.json().get("guias", []):
                    material = guia.get("nome_material", "Sem Nome")
                    data = guia.get("data_recebimento", "Sem Data")
                    
                    cartao = ft.Card(
                        elevation=2,
                        content=ft.ListTile(
                            leading=ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN, size=40),
                            title=ft.Text(f"Material: {material}", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"Recebido em: {data}\nStatus: Concluído e Assinado"),
                            trailing=ft.IconButton(icon=ft.icons.DONE_ALL, icon_color=ft.colors.GREEN)
                        )
                    )
                    aba_assinadas.controls.append(cartao)

            page.update()
        except Exception as ex:
            print(f"Erro ao carregar dados: {ex}")

    carregar_guias()

    # ==========================================
    # 5. ESTRUTURA DE ABAS
    # ==========================================
    controle_abas = ft.Tabs(
        selected_index=0,
        expand=True,
        tabs=[
            ft.Tab(text="Recebimento", icon=ft.icons.ASSIGNMENT_RETURNED, content=ft.Container(content=aba_pendentes, padding=15)),
            ft.Tab(text="Assinadas", icon=ft.icons.ASSIGNMENT_TURNED_IN, content=ft.Container(content=aba_assinadas, padding=15)),
        ]
    )
    page.add(controle_abas)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=porta, host="0.0.0.0", upload_dir=PASTA_UPLOADS, secret_key="chave_secreta_guias_123")