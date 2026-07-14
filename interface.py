import flet as ft
import requests
import os

# O seu novo endereço oficial da API na nuvem!
URL_BASE = "https://controle-guias.onrender.com"

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

    # ==========================================
    # 2. SELETORES DE ARQUIVOS
    # ==========================================
    seletor_nova_guia = ft.FilePicker()
    seletor_assinatura = ft.FilePicker()

    async def selecionar_arquivo_inicial(e):
        arquivos = await seletor_nova_guia.pick_files(allowed_extensions=["pdf"])
        if arquivos:
            caminho_pdf_selecionado[0] = arquivos[0].path
            botao_anexar.text = f"PDF: {arquivos[0].name}"
            page.update()

    # ==========================================
    # 3. JANELA DE CADASTRAR NOVA GUIA
    # ==========================================
    campo_material = ft.TextField(label="Nome do Material", width=300)
    campo_data = ft.TextField(label="Data de Recebimento", width=300)
    botao_anexar = ft.FilledButton("Anexar PDF Inicial", icon=ft.Icons.UPLOAD_FILE, on_click=selecionar_arquivo_inicial)

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
            return
            
        url_api = f"{URL_BASE}/guias/upload"
        dados = {"nome_material": campo_material.value, "data_recebimento": campo_data.value}
        arquivos = {"ficheiro_pdf": open(caminho_pdf_selecionado[0], "rb")}
        
        try:
            resposta = requests.post(url_api, data=dados, files=arquivos)
            if resposta.status_code == 200:
                campo_material.value = ""
                campo_data.value = ""
                botao_anexar.text = "Anexar PDF Inicial"
                caminho_pdf_selecionado[0] = None
                fechar_dialogo()
                carregar_guias() 
        except Exception as ex:
            print(f"Erro na API: {ex}")

    dialogo_nova_guia.actions = [
        ft.TextButton("Cancelar", on_click=fechar_dialogo),
        ft.FilledButton("Salvar", on_click=salvar_guia, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE))
    ]

    page.floating_action_button = ft.FloatingActionButton(
        content=ft.Row([ft.Icon(ft.Icons.ADD), ft.Text("Nova Guia", color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.CENTER, tight=True),
        bgcolor=ft.Colors.BLUE_ACCENT, width=130,
        on_click=lambda e: setattr(dialogo_nova_guia, 'open', True) or page.update()
    )

    # ==========================================
    # 4. LISTAS VISUAIS DINÂMICAS E ATUALIZAÇÃO
    # ==========================================
    aba_pendentes = ft.ListView(expand=True, controls=[])
    aba_assinadas = ft.ListView(expand=True, controls=[])

    def criar_acao_assinar(nome):
        async def acao(e):
            arquivos = await seletor_assinatura.pick_files(allowed_extensions=["pdf"])
            if arquivos:
                caminho_pdf = arquivos[0].path
                url_api = f"{URL_BASE}/guias/{nome}/assinar"
                req_arquivos = {"ficheiro_pdf_assinado": open(caminho_pdf, "rb")}
                try:
                    resposta = requests.put(url_api, files=req_arquivos)
                    if resposta.status_code == 200:
                        print(f"Sucesso: {nome} assinado!")
                        carregar_guias() 
                except Exception as ex:
                    print(f"Erro ao assinar: {ex}")
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
                            leading=ft.Icon(ft.Icons.PICTURE_AS_PDF, color=ft.Colors.RED_ACCENT, size=40),
                            title=ft.Text(f"Material: {material}", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"Recebido em: {data}\nStatus: Pendente Assinatura"),
                            trailing=ft.FilledButton(
                                "Assinar", 
                                icon=ft.Icons.EDIT, 
                                color=ft.Colors.WHITE, 
                                bgcolor=ft.Colors.ORANGE_ACCENT, 
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
                            leading=ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=40),
                            title=ft.Text(f"Material: {material}", weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"Recebido em: {data}\nStatus: Concluído e Assinado"),
                            trailing=ft.IconButton(icon=ft.Icons.DONE_ALL, icon_color=ft.Colors.GREEN)
                        )
                    )
                    aba_assinadas.controls.append(cartao)

            page.update()
        except Exception as ex:
            print(f"Erro ao carregar dados: {ex}")

    carregar_guias()

    # ==========================================
    # 5. ESTRUTURA DE ABAS (TABS)
    # ==========================================
    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Recebimento", icon=ft.Icons.ASSIGNMENT_RETURNED),
            ft.Tab(label="Assinadas", icon=ft.Icons.ASSIGNMENT_TURNED_IN),
        ]
    )

    tab_view = ft.TabBarView(
        expand=True,
        controls=[
            ft.Container(content=aba_pendentes, padding=15),
            ft.Container(content=aba_assinadas, padding=15),
        ]
    )

    controle_abas = ft.Tabs(length=2, selected_index=0, expand=True, content=ft.Column(expand=True, controls=[tab_bar, tab_view]))
    page.add(controle_abas)

if __name__ == "__main__":
    # Configuração obrigatória para o Flet rodar na web (Render)
    porta = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=porta, host="0.0.0.0")