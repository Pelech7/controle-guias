import flet as ft
import requests
import os

URL_BASE = "https://controle-guias.onrender.com"
PASTA_UPLOADS = "uploads_temporarios"
os.makedirs(PASTA_UPLOADS, exist_ok=True)

def main(page: ft.Page):
    # ==========================================
    # 1. CONFIGURAÇÕES DA PÁGINA E ALERTAS
    # ==========================================
    page.title = "Controle de Guias de Recebimento"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 450
    page.window_height = 800
    page.padding = 0

    caminho_pdf_selecionado = [None]

    def mostrar_aviso(mensagem, cor=ft.colors.RED):
        page.snack_bar = ft.SnackBar(ft.Text(mensagem), bgcolor=cor)
        page.snack_bar.open = True
        page.update()

    # ==========================================
    # 2. SELETORES DE ARQUIVOS (VERSÃO WEB)
    # ==========================================
    seletor_nova_guia = ft.FilePicker()
    seletor_assinatura = ft.FilePicker()

    def ao_selecionar_nova_guia(e: ft.FilePickerResultEvent):
        if e.files:
            nome_arquivo = e.files[0].name
            seletor_nova_guia.upload([
                ft.FilePickerUploadFile(nome_arquivo, upload_url=page.get_upload_url(nome_arquivo, 60))
            ])
            caminho_pdf_selecionado[0] = os.path.join(PASTA_UPLOADS, nome_arquivo)
            botao_anexar.text = f"PDF: {nome_arquivo}"
            page.update()

    seletor_nova_guia.on_result = ao_selecionar_nova_guia
    page.overlay.append(seletor_nova_guia)
    page.overlay.append(seletor_assinatura)

    # ==========================================
    # 3. JANELA DE CADASTRAR NOVA GUIA
    # ==========================================
    campo_material = ft.TextField(label="Nome do Material", width=300)
    campo_data = ft.TextField(label="Data de Recebimento", width=300)
    
    botao_anexar = ft.FilledButton(
        "Anexar PDF Inicial", 
        icon=ft.icons.UPLOAD_FILE, 
        on_click=lambda _: seletor_nova_guia.pick_files(allowed_extensions=["pdf"])
    )

    dialogo_nova_guia = ft.AlertDialog(
        title=ft.Text("Cadastrar Novo Material"),
        content=ft.Column([campo_material, campo_data, botao_anexar], tight=True),
    )
    page.overlay.append(dialogo_nova_guia)

    def fechar_dialogo(e=None):
        dialogo_nova_guia.open = False
        page.update()

    def salvar_guia(e):
        if not caminho_pdf_selecionado[0]:
            mostrar_aviso("Nenhum PDF foi selecionado!")
            return
            
        if not os.path.exists(caminho_pdf_selecionado[0]):
            mostrar_aviso("A processar o anexo... clique em Salvar novamente num instante.", ft.colors.ORANGE)
            return
            
        url_api = f"{URL_BASE}/guias/upload"
        dados = {"nome_material": campo_material.value, "data_recebimento": campo_data.value}
        
        try:
            with open(caminho_pdf_selecionado[0], "rb") as f:
                arquivos = {"ficheiro_pdf": f}
                resposta = requests.post(url_api, data=dados, files=arquivos)
            
            if resposta.status_code == 200:
                campo_material.value = ""
                campo_data.value = ""
                botao_anexar.text = "Anexar PDF Inicial"
                caminho_pdf_selecionado[0] = None
                fechar_dialogo()
                carregar_guias() 
                mostrar_aviso("Guia salva com sucesso!", ft.colors.GREEN)
            else:
                mostrar_aviso(f"Erro do servidor: {resposta.text}")
        except Exception as ex:
            mostrar_aviso(f"Erro de conexão com a API: {ex}")

    dialogo_nova_guia.actions = [
        ft.TextButton("Cancelar", on_click=fechar_dialogo),
        ft.FilledButton("Salvar", on_click=salvar_guia, style=ft.ButtonStyle(bgcolor=ft.colors.GREEN, color=ft.colors.WHITE))
    ]

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

    def criar_acao_assinar(nome):
        def acao(e):
            mostrar_aviso(f"Em desenvolvimento para: {nome}", ft.colors.BLUE)
        return acao

    def carregar_guias():
        aba_pendentes.controls.clear()
        aba_assinadas.controls.clear()
        
        try:
            resp_pendentes = requests.get(f"{URL_BASE}/guias/pendentes")
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
                                "Assinar", 
                                icon=ft.icons.EDIT, 
                                color=ft.colors.WHITE, 
                                bgcolor=ft.colors.ORANGE_ACCENT, 
                                on_click=criar_acao_assinar(material)
                            )
                        )
                    )
                    aba_pendentes.controls.append(cartao)

            resp_assinadas = requests.get(f"{URL_BASE}/guias/assinadas")
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
    # 5. ESTRUTURA DE ABAS (CORRIGIDA)
    # ==========================================
    controle_abas = ft.Tabs(
        selected_index=0,
        expand=True,
        tabs=[
            ft.Tab(
                text="Recebimento",
                icon=ft.icons.ASSIGNMENT_RETURNED,
                content=ft.Container(content=aba_pendentes, padding=15)
            ),
            ft.Tab(
                text="Assinadas",
                icon=ft.icons.ASSIGNMENT_TURNED_IN,
                content=ft.Container(content=aba_assinadas, padding=15)
            ),
        ]
    )
    page.add(controle_abas)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=porta, host="0.0.0.0", upload_dir=PASTA_UPLOADS)