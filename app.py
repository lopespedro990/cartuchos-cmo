import streamlit as st  # Importa a biblioteca Streamlit para criar a interface web interativa.
import pandas as pd  # Importa o Pandas para manipulação e análise de dados, usado para DataFrames.
import plotly.express as px  # Importa o Plotly Express para criação de gráficos interativos de forma simples.
from supabase import create_client, Client  # Importa funções para criar um cliente Supabase, que é um backend de banco de dados.
from datetime import datetime  # Importa a classe datetime para lidar com datas e horários.

# --- CONFIGURAÇÃO DA PÁGINA E SUPABASE ---
st.set_page_config(layout="wide", page_title="Gerenciador de Suprimentos")  # Configura a página Streamlit para layout largo e título da página.

@st.cache_resource  # Decorador que cacheia o recurso (conexão Supabase) para reutilização eficiente.
def init_connection():  # Define uma função para inicializar a conexão com o Supabase.
    url = st.secrets["supabase"]["url"]  # Obtém a URL do Supabase dos segredos do Streamlit.
    key = st.secrets["supabase"]["key"]  # Obtém a chave do Supabase dos segredos do Streamlit.
    return create_client(url, key)  # Cria e retorna o cliente Supabase.

supabase = init_connection()  # Inicializa a conexão com o Supabase e armazena na variável global.

# --- FUNÇÕES DA APLICAÇÃO ---
def get_users():  # Define uma função para obter todos os usuários (setores) do banco de dados.
    response = supabase.table('usuarios').select('id, name').order('name').execute()  # Consulta a tabela 'usuarios' selecionando id e name, ordenado por name.
    return response.data  # Retorna os dados da resposta.

def get_change_logs():  # Define uma função para obter os logs de trocas de cartuchos, incluindo joins com outras tabelas.
    response = supabase.table('trocas_cartucho').select('*, usuarios(name), equipamentos(modelo), suprimentos(modelo, categoria, tipo)').order('data_troca', desc=True).execute()  # Consulta a tabela 'trocas_cartucho' com joins e ordenado por data_troca descendente.
    return response.data  # Retorna os dados da resposta.

def get_equipamentos(setor_id=None):  # Define uma função para obter equipamentos, opcionalmente filtrado por setor_id.
    query = supabase.table('equipamentos').select('id, modelo, categoria, usuarios(name)').order('modelo')  # Inicia a query base para equipamentos, selecionando campos e ordenando por modelo.
    if setor_id:  # Se setor_id for fornecido,
        query = query.eq('setor_id', setor_id)  # Filtra pela coluna setor_id.
    response = query.execute()  # Executa a query.
    return response.data  # Retorna os dados.

def get_suprimentos(categoria=None):  # Define uma função para obter suprimentos, opcionalmente filtrado por categoria.
    query = supabase.table('suprimentos').select('*').order('modelo')  # Inicia a query base para suprimentos, ordenando por modelo.
    if categoria:  # Se categoria for fornecida,
        query = query.eq('categoria', categoria)  # Filtra pela categoria.
    response = query.execute()  # Executa a query.
    return response.data  # Retorna os dados.

# --- APLICAÇÃO PRINCIPAL ---
def run_app():  # Define a função principal que executa a aplicação Streamlit.
    logo_url = "https://www.camaraourinhos.sp.gov.br/img/customizacao/cliente/facebook/imagem_compartilhamento_redes.jpg"  # Define a URL do logo.
    st.sidebar.image(logo_url, use_container_width=True)  # Exibe o logo na barra lateral, ajustando à largura do container.

    st.title("🖨️ Gerenciador de Suprimentos de Impressão")  # Define o título principal da aplicação.
    st.markdown("---")  # Adiciona uma linha horizontal para separação visual.

    page = st.sidebar.radio("Selecione uma página", ["Registrar Troca", "Dashboard de Análise", "Gerenciar Setores", "Gerenciar Equipamentos", "Gerenciar Suprimentos"])  # Cria um rádio button na barra lateral para selecionar a página.

    # --- PÁGINA: REGISTRAR TROCA ---
    if page == "Registrar Troca":  # Verifica se a página selecionada é "Registrar Troca".
        st.header("Registrar uma Nova Troca de Suprimento")  # Define o cabeçalho da página.
        users = get_users()  # Obtém a lista de usuários (setores).
        if not users:  # Se não houver usuários,
            st.warning("Nenhum setor cadastrado.")  # Exibe um aviso.
        else:  # Caso contrário,
            user_map = {user['name']: user['id'] for user in users}  # Cria um mapa de nomes para IDs de usuários.
            selected_user_name = st.selectbox("1. Selecione o Setor:", options=user_map.keys(), index=None, placeholder="Escolha um setor...")  # Cria um selectbox para selecionar o setor.
            if selected_user_name:  # Se um setor for selecionado,
                selected_user_id = user_map[selected_user_name]  # Obtém o ID do setor selecionado.
                equipamentos_no_setor = get_equipamentos(setor_id=selected_user_id)  # Obtém equipamentos do setor.

                if not equipamentos_no_setor:  # Se não houver equipamentos,
                    st.warning(f"O setor '{selected_user_name}' não possui equipamentos cadastrados.")  # Exibe aviso.
                else:  # Caso contrário,
                    equipamento_map = {eq['modelo']: {'id': eq['id'], 'categoria': eq['categoria']} for eq in equipamentos_no_setor}  # Cria mapa de modelos de equipamentos para IDs e categorias.
                    selected_equipamento_modelo = st.selectbox("2. Selecione o Equipamento:", options=equipamento_map.keys(), index=None, placeholder="Escolha um equipamento...")  # Selectbox para equipamento.
                    if selected_equipamento_modelo:  # Se equipamento for selecionado,
                        selected_equipamento_id = equipamento_map[selected_equipamento_modelo]['id']  # Obtém ID do equipamento.
                        categoria_do_equipamento = equipamento_map[selected_equipamento_modelo]['categoria']  # Obtém categoria do equipamento.
                        if not categoria_do_equipamento:  # Se categoria não estiver definida,
                            st.error(f"O equipamento '{selected_equipamento_modelo}' não tem uma categoria definida. Por favor, edite-o na página 'Gerenciar Equipamentos'.")  # Exibe erro.
                        else:  # Caso contrário,
                            suprimentos_disponiveis = get_suprimentos(categoria=categoria_do_equipamento)  # Obtém suprimentos da categoria.

                            if not suprimentos_disponiveis:  # Se não houver suprimentos,
                                st.warning(f"Nenhum suprimento da categoria '{categoria_do_equipamento}' cadastrado. Vá para 'Gerenciar Suprimentos' para adicionar.")  # Exibe aviso.
                            else:  # Caso contrário,
                                suprimento_map = {f"{sup['modelo']} ({sup['tipo']})": sup['id'] for sup in suprimentos_disponiveis}  # Cria mapa de suprimentos formatados para IDs.
                                st.markdown("---")  # Linha horizontal.
                                with st.form("registro_troca_form"):  # Inicia um formulário para registro de troca.
                                    st.info(f"Registrando para: **{selected_user_name}** | **{selected_equipamento_modelo}**")  # Exibe informação sobre o registro.

                                    suprimento_selecionado_modelo = st.selectbox("3. Selecione o Suprimento Trocado:", options=suprimento_map.keys())  # Selectbox para suprimento.
                                    change_date = st.date_input("4. Data da Troca:", datetime.now())  # Input de data com valor default atual.

                                    observacao = st.text_area("5. Observações (opcional):", placeholder="Ex: Cartucho antigo falhando, manchando a página, etc.")  # Área de texto para observações.

                                    if st.form_submit_button("Registrar Troca"):  # Botão de submissão do formulário.
                                        if not suprimento_selecionado_modelo:  # Se suprimento não selecionado,
                                            st.error("Por favor, selecione um suprimento.")  # Exibe erro.
                                        else:  # Caso contrário,
                                            suprimento_id = suprimento_map[suprimento_selecionado_modelo]  # Obtém ID do suprimento.
                                            formatted_date = change_date.strftime("%Y-%m-%d")  # Formata a data.
                                            try:  # Tenta inserir no banco.
                                                supabase.table('trocas_cartucho').insert({
                                                    'usuario_id': selected_user_id,
                                                    'equipamento_id': selected_equipamento_id,
                                                    'data_troca': formatted_date,
                                                    'suprimento_id': suprimento_id,
                                                    'observacao': observacao
                                                }).execute()  # Insere os dados na tabela.
                                                st.success("Registro de troca criado com sucesso!")  # Exibe sucesso.
                                            except Exception as e:  # Captura exceções.
                                                st.error(f"Falha ao registrar: {e}")  # Exibe erro.

    # --- PÁGINA: DASHBOARD DE ANÁLISE ---
    elif page == "Dashboard de Análise":  # Verifica se a página é "Dashboard de Análise".
        st.header("Dashboard de Análise de Trocas")  # Cabeçalho da página.

        if 'sort_by' not in st.session_state:  # Inicializa estado de sessão para ordenação se não existir.
            st.session_state.sort_by = 'Data'  # Define ordenação default por 'Data'.
            st.session_state.sort_ascending = False  # Ordenação descendente.
        if 'deleting_log_id' not in st.session_state:  # Inicializa estado para ID de log a deletar.
            st.session_state.deleting_log_id = None  # Valor inicial None.
        logs = get_change_logs()  # Obtém logs de trocas.
        if not logs:  # Se não houver logs,
            st.info("Ainda não há registros de troca para exibir.")  # Exibe info.
        else:  # Caso contrário,
            processed_logs = []  # Inicializa lista para logs processados.
            for log in logs:  # Itera sobre cada log.
                processed_logs.append({  # Adiciona dicionário processado com campos mapeados, lidando com valores default.
                    'ID Troca': log.get('id'),
                    'Data': log.get('data_troca'),
                    'Setor': log.get('usuarios', {}).get('name', 'Setor Desconhecido'),
                    'Equipamento': log.get('equipamentos', {}).get('modelo', 'Não especificado'),
                    'Suprimento': log.get('suprimentos', {}).get('modelo', 'Não especificado'),
                    'Categoria': log.get('suprimentos', {}).get('categoria', 'Não definida'),
                    'Tipo': log.get('suprimentos', {}).get('tipo', 'Não definido'),
                    'Observação': log.get('observacao', '')
                })

            df = pd.DataFrame(processed_logs)  # Cria DataFrame a partir dos logs processados.
            df['Data'] = pd.to_datetime(df['Data'])  # Converte coluna 'Data' para datetime.

            st.sidebar.markdown("---")  # Linha horizontal na barra lateral.
            st.sidebar.header("Filtros do Dashboard")  # Cabeçalho para filtros na barra lateral.

            # Filtro de Categoria
            categorias_filtro = ["Todas"] + sorted(df[df['Categoria'] != 'Não definida']['Categoria'].unique().tolist())  # Cria lista de categorias únicas, adicionando "Todas".
            categoria_filtrada = st.sidebar.selectbox("Filtrar por Categoria:", categorias_filtro)  # Selectbox para filtro de categoria.

            # NOVO FILTRO DE SETOR
            setores_filtro = ["Todos"] + sorted(df['Setor'].unique().tolist())  # Lista de setores únicos, adicionando "Todos".
            setor_filtrado = st.sidebar.selectbox("Filtrar por Setor:", setores_filtro)  # Selectbox para filtro de setor.
            # Filtro de Mês/Ano
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')  # Cria coluna 'AnoMês' formatada.
            lista_meses = ["Todos"] + sorted(df['AnoMês'].unique(), reverse=True)  # Lista de meses únicos, adicionando "Todos", ordenado reverso.
            mes_selecionado = st.sidebar.selectbox("Filtrar por Mês/Ano:", options=lista_meses)  # Selectbox para filtro de mês/ano.

            # APLICAÇÃO DOS FILTROS
            df_filtrado = df.copy()  # Copia o DataFrame original para filtragem.
            if categoria_filtrada != "Todas":  # Aplica filtro de categoria se não "Todas".
                df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_filtrada]
            if setor_filtrado != "Todos":  # Aplica filtro de setor se não "Todos".
                df_filtrado = df_filtrado[df_filtrado['Setor'] == setor_filtrado]
            if mes_selecionado != "Todos":  # Aplica filtro de mês se não "Todos".
                df_filtrado = df_filtrado[df_filtrado['AnoMês'] == mes_selecionado]

            st.markdown("### Gráficos de Análise")  # Subcabeçalho para gráficos.

            if df_filtrado.empty:  # Se DataFrame filtrado estiver vazio,
                st.warning("Nenhum registro encontrado para os filtros selecionados.")  # Exibe aviso.
            else:  # Caso contrário,
                col1, col2 = st.columns(2)  # Cria duas colunas para gráficos.
                with col1:  # Na primeira coluna,
                    # LÓGICA DO GRÁFICO DE BARRAS INTELIGENTE
                    if setor_filtrado != "Todos":  # Se setor filtrado,
                        st.subheader("Total de Trocas por Equipamento")  # Subcabeçalho para trocas por equipamento.
                        counts = df_filtrado['Equipamento'].value_counts().reset_index()  # Conta ocorrências por equipamento.
                        counts.columns = ['Equipamento', 'Total de Trocas']  # Renomeia colunas.
                        x_axis, label_x = 'Equipamento', 'Equipamento'  # Define eixos para equipamento.
                    else:  # Caso contrário,
                        st.subheader("Total de Trocas por Setor")  # Subcabeçalho para trocas por setor.
                        counts = df_filtrado['Setor'].value_counts().reset_index()  # Conta por setor.
                        counts.columns = ['Setor', 'Total de Trocas']  # Renomeia colunas.
                        x_axis, label_x = 'Setor', 'Nome do Setor'  # Define eixos para setor.
                    # Título do gráfico atualizado
                    titulo_grafico_bar = f"Filtros: ({setor_filtrado}, {categoria_filtrada}, {mes_selecionado})"  # Título com filtros.
                    fig_bar = px.bar(counts, x=x_axis, y='Total de Trocas', title=titulo_grafico_bar, labels={x_axis: label_x, 'Total de Trocas': 'Quantidade'}, text='Total de Trocas')  # Cria gráfico de barras.
                    fig_bar.update_traces(textposition='outside')  # Atualiza posição do texto.
                    st.plotly_chart(fig_bar, use_container_width=True)  # Exibe o gráfico.
                with col2:  # Na segunda coluna,
                    st.subheader("Proporção por Tipo de Suprimento")  # Subcabeçalho para proporção por tipo.
                    type_counts = df_filtrado['Tipo'].value_counts().reset_index()  # Conta por tipo.
                    type_counts.columns = ['Tipo', 'Quantidade']  # Renomeia colunas.
                    # Título do gráfico atualizado
                    titulo_grafico_pie = f"Filtros: ({setor_filtrado}, {categoria_filtrada}, {mes_selecionado})"  # Título com filtros.
                    fig_pie = px.pie(type_counts, names='Tipo', values='Quantidade', title=titulo_grafico_pie, hole=.3)  # Cria gráfico de pizza com buraco.
                    st.plotly_chart(fig_pie, use_container_width=True)  # Exibe o gráfico.
                st.subheader("Trocas ao Longo do Tempo")  # Subcabeçalho para trocas ao longo do tempo.
                monthly_changes = df.groupby('AnoMês').size().reset_index(name='Quantidade')  # Agrupa por mês e conta.
                if setor_filtrado != "Todos":  # Se setor filtrado,
                    monthly_changes = df_filtrado.groupby('AnoMês').size().reset_index(name='Quantidade')  # Usa DataFrame filtrado.

                # Título do gráfico atualizado
                titulo_grafico_linha = f"Volume de Trocas por Mês ({setor_filtrado}, {categoria_filtrada})"  # Título com filtros.
                fig_line = px.line(monthly_changes.sort_values(by='AnoMês'), x='AnoMês', y='Quantidade', title=titulo_grafico_linha, markers=True, labels={'AnoMês': 'Mês/Ano', 'Quantidade': 'Nº de Trocas'})  # Cria gráfico de linha.
                st.plotly_chart(fig_line, use_container_width=True)  # Exibe o gráfico.

            st.markdown("---")  # Linha horizontal.
            col_titulo, col_download = st.columns([3, 1])  # Cria colunas para título e download.
            with col_titulo:  # Na coluna de título,
                # Título do histórico atualizado
                titulo_historico = f"Histórico de Trocas ({setor_filtrado}, {categoria_filtrada}, {mes_selecionado})"  # Título com filtros.
                st.subheader(titulo_historico)  # Exibe subcabeçalho.

            with col_download:  # Na coluna de download,
                @st.cache_data  # Cacheia a função de conversão para CSV.
                def convert_df_to_csv(df_to_convert):  # Define função para converter DataFrame para CSV.
                    return df_to_convert.to_csv(index=False).encode('utf-8')  # Converte sem índice e codifica em UTF-8.
                df_export = df_filtrado[['Data', 'Setor', 'Equipamento', 'Suprimento', 'Categoria', 'Tipo', 'Observação']].copy()  # Copia colunas selecionadas para exportação.
                df_export['Data'] = pd.to_datetime(df_export['Data']).dt.strftime('%d/%m/%Y')  # Formata data para DD/MM/YYYY.

                csv = convert_df_to_csv(df_export)  # Converte para CSV.

                # Nome do arquivo de exportação atualizado
                st.download_button(  # Botão para download de CSV.
                    label="📥 Exportar para CSV",
                    data=csv,
                    file_name=f'historico_trocas_{setor_filtrado}_{categoria_filtrada}_{mes_selecionado}.csv',
                    mime='text/csv',
                )
            if st.session_state.deleting_log_id is not None:  # Se houver ID de log para deletar,
                log_details = df[df['ID Troca'] == st.session_state.deleting_log_id].iloc[0]  # Obtém detalhes do log.
                st.warning(f"Você tem certeza que deseja apagar o registro abaixo?")  # Exibe aviso.
                st.write(f"**Data:** {log_details['Data'].strftime('%d/%m/%Y')}, **Setor:** {log_details['Setor']}, **Equipamento:** {log_details['Equipamento']}, **Suprimento:** {log_details['Suprimento']}")  # Exibe detalhes.
                with st.form("confirm_delete_log_form"):  # Formulário de confirmação de deleção.
                    password = st.text_input("Para confirmar, digite a senha de exclusão:", type="password")  # Input de senha.
                    col_confirm, col_cancel = st.columns(2)  # Colunas para botões.
                    with col_confirm:  # Coluna de confirmação,
                        if st.form_submit_button("Sim, apagar registro", type="primary"):  # Botão de apagar.
                            if password == st.secrets["auth"].get("delete_password", st.secrets["auth"]["password"]):  # Verifica senha.
                                try:  # Tenta deletar.
                                    supabase.table('trocas_cartucho').delete().eq('id', st.session_state.deleting_log_id).execute()  # Deleta o registro.
                                    st.success("Registro apagado com sucesso!")  # Sucesso.
                                    st.session_state.deleting_log_id = None  # Reseta estado.
                                    st.rerun()  # Recarrega a app.
                                except Exception as e:  # Captura erro.
                                    st.error(f"Ocorreu um erro ao apagar o registro: {e}")  # Exibe erro.
                            else:  # Senha incorreta.
                                st.error("Senha de exclusão incorreta.")
                    with col_cancel:  # Coluna de cancelar,
                        if st.form_submit_button("Cancelar"):  # Botão de cancelar.
                            st.session_state.deleting_log_id = None  # Reseta estado.
                            st.rerun()  # Recarrega.

            def set_sort_order(column_name):  # Define função para alterar ordenação.
                if st.session_state.sort_by == column_name:  # Se já ordenando pela coluna,
                    st.session_state.sort_ascending = not st.session_state.sort_ascending  # Inverte ordem.
                else:  # Caso contrário,
                    st.session_state.sort_by = column_name  # Define nova coluna.
                    st.session_state.sort_ascending = True  # Ordem ascendente.
                st.session_state.deleting_log_id = None  # Reseta deleção.

            df_sorted = df_filtrado.sort_values(by=st.session_state.sort_by, ascending=st.session_state.sort_ascending)  # Ordena o DataFrame filtrado.
            header_cols = st.columns([2, 3, 3, 3, 2, 2, 1, 1])  # Cria colunas para cabeçalhos da tabela.
            if header_cols[0].button('Data'): set_sort_order('Data')  # Botão para ordenar por Data.
            if header_cols[1].button('Setor'): set_sort_order('Setor')  # Por Setor.
            if header_cols[2].button('Equipamento'): set_sort_order('Equipamento')  # Por Equipamento.
            if header_cols[3].button('Suprimento'): set_sort_order('Suprimento')  # Por Suprimento.
            if header_cols[4].button('Categoria'): set_sort_order('Categoria')  # Por Categoria.
            if header_cols[5].button('Tipo'): set_sort_order('Tipo')  # Por Tipo.
            header_cols[6].write("**OBS**")  # Cabeçalho para observações.
            header_cols[7].write("**Ação**")  # Para ações.
            st.markdown("<hr style='margin-top: -0.5em; margin-bottom: 0.5em;'>", unsafe_allow_html=True)  # Linha horizontal customizada.

            for index, row in df_sorted.iterrows():  # Itera sobre linhas ordenadas.
                row_cols = st.columns([2, 3, 3, 3, 2, 2, 1, 1])  # Colunas para cada linha.
                row_cols[0].text(row['Data'].strftime('%d/%m/%Y'))  # Exibe data formatada.
                row_cols[1].text(row['Setor'])  # Setor.
                row_cols[2].text(row['Equipamento'])  # Equipamento.
                row_cols[3].text(row['Suprimento'])  # Suprimento.
                row_cols[4].text(row['Categoria'])  # Categoria.
                row_cols[5].text(row['Tipo'])  # Tipo.

                obs_text = row['Observação']  # Obtém observação.
                if pd.notna(obs_text) and obs_text.strip():  # Se observação não vazia,
                    with row_cols[6].popover("👁️", help="Ver observação"):  # Popover para ver observação.
                        st.info(obs_text)  # Exibe info.
                else:  # Caso vazio,
                    row_cols[6].write("")  # Escreve vazio.

                if row_cols[7].button("🗑️", key=f"del_log_{row['ID Troca']}", help="Remover este registro"):  # Botão de deletar.
                    st.session_state.deleting_log_id = row['ID Troca']  # Define ID para deleção.
                    st.rerun()  # Recarrega.

    # --- PÁGINA: GERENCIAR SETORES ---
    elif page == "Gerenciar Setores":  # Verifica página "Gerenciar Setores".
        st.header("Gerenciar Setores")  # Cabeçalho.
        if 'editing_sector_id' not in st.session_state:  # Inicializa estado para edição de setor.
            st.session_state.editing_sector_id = None

        if 'deleting_sector_id' not in st.session_state:  # Inicializa estados para deleção de setor.
            st.session_state.deleting_sector_id, st.session_state.deleting_sector_name, st.session_state.deleting_sector_logs_count = None, None, 0

        if st.session_state.deleting_sector_id is not None:  # Se deletando setor,
            st.warning(f"⚠️ **ATENÇÃO:** Você está prestes a apagar o setor **'{st.session_state.deleting_sector_name}'** e todos os seus **{st.session_state.deleting_sector_logs_count}** registros. Esta ação é irreversível.")  # Aviso.
            with st.form("confirm_delete_form"):  # Formulário de confirmação.
                password = st.text_input("Para confirmar, digite a senha de exclusão:", type="password")  # Input senha.
                col_confirm, col_cancel = st.columns(2)  # Colunas.
                with col_confirm:  # Confirmação,
                    if st.form_submit_button("Confirmar Exclusão Permanente", type="primary"):  # Botão confirmar.
                        if password == st.secrets["auth"].get("delete_password", st.secrets["auth"]["password"]):  # Verifica senha.
                            try:  # Tenta deletar.
                                supabase.table('trocas_cartucho').delete().eq('usuario_id', st.session_state.deleting_sector_id).execute()  # Deleta logs relacionados.
                                supabase.table('usuarios').delete().eq('id', st.session_state.deleting_sector_id).execute()  # Deleta setor.
                                st.success(f"O setor '{st.session_state.deleting_sector_name}' e seus registros foram removidos com sucesso!")  # Sucesso.
                                st.session_state.deleting_sector_id = None  # Reseta.
                                st.rerun()  # Recarrega.
                            except Exception as e:  # Erro.
                                st.error(f"Ocorreu um erro durante a exclusão: {e}")
                        else:  # Senha errada.
                            st.error("Senha de exclusão incorreta. A ação não foi realizada.")
                with col_cancel:  # Cancelar,
                    if st.form_submit_button("Cancelar"):  # Botão cancelar.
                        st.session_state.deleting_sector_id = None  # Reseta.
                        st.rerun()  # Recarrega.
        else:  # Caso não deletando,
            with st.expander("Adicionar Novo Setor", expanded=(st.session_state.editing_sector_id is None)):  # Expander para adicionar setor.
                with st.form("novo_setor_form", clear_on_submit=True):  # Formulário.
                    new_user_name = st.text_input("Nome do Novo Setor:")  # Input nome.
                    if st.form_submit_button("Adicionar Setor"):  # Botão submeter.
                        if new_user_name:  # Se nome preenchido,
                            try:  # Tenta inserir.
                                supabase.table('usuarios').insert({'name': new_user_name}).execute()  # Insere setor.
                                st.success(f"Setor '{new_user_name}' adicionado!")  # Sucesso.
                                st.rerun()  # Recarrega.
                            except Exception as e:  # Erro.
                                st.error(f"Ocorreu um erro: {e}")
            st.markdown("---")  # Linha.
            st.subheader("Lista de Setores Cadastrados")  # Subcabeçalho.
            users_data = get_users()  # Obtém setores.
            if not users_data:  # Se vazio,
                st.info("Nenhum setor cadastrado.")  # Info.
            else:  # Caso contrário,
                for user in users_data:  # Itera sobre setores.
                    user_id, user_name = user['id'], user['name']  # Extrai ID e nome.
                    with st.container(border=True):  # Container com borda.
                        if st.session_state.editing_sector_id == user_id:  # Se editando este setor,
                            col1, col2, col3 = st.columns([0.8, 0.1, 0.1])  # Colunas para edição.
                            with col1:  # Coluna input,
                                new_name = st.text_input("Novo nome:", value=user_name, key=f"edit_input_{user_id}", label_visibility="collapsed")  # Input novo nome.
                            with col2:  # Coluna salvar,
                                if st.button("✔️", key=f"save_{user_id}", help="Salvar alterações"):  # Botão salvar.
                                    if new_name and new_name != user_name:  # Se nome novo diferente,
                                        try:  # Tenta atualizar.
                                            supabase.table('usuarios').update({'name': new_name}).eq('id', user_id).execute()  # Atualiza nome.
                                            st.success(f"Setor renomeado para '{new_name}'!")  # Sucesso.
                                            st.session_state.editing_sector_id = None  # Reseta edição.
                                            st.rerun()  # Recarrega.
                                        except Exception as e:  # Erro.
                                            st.error(f"Erro ao atualizar: {e}")
                                    else:  # Nome igual ou vazio,
                                        st.session_state.editing_sector_id = None  # Reseta.
                                        st.rerun()  # Recarrega.
                            with col3:  # Coluna cancelar,
                                if st.button("✖️", key=f"cancel_{user_id}", help="Cancelar edição"):  # Botão cancelar.
                                    st.session_state.editing_sector_id = None  # Reseta.
                                    st.rerun()  # Recarrega.
                        else:  # Não editando,
                            is_editing_another = st.session_state.editing_sector_id is not None  # Verifica se editando outro.
                            col1, col2, col3 = st.columns([0.8, 0.1, 0.1])  # Colunas.
                            col1.markdown(f"<p style='margin-top: 5px; font-size: 1.1em;'>{user_name}</p>", unsafe_allow_html=True)  # Exibe nome com estilo.

                            if col2.button("✏️", key=f"edit_{user_id}", help=f"Editar '{user_name}'", disabled=is_editing_another):  # Botão editar, desabilitado se editando outro.
                                st.session_state.editing_sector_id = user_id  # Define para edição.
                                st.rerun()  # Recarrega.
                            if col3.button("🗑️", key=f"delete_{user_id}", help=f"Remover '{user_name}'", disabled=is_editing_another):  # Botão deletar.
                                response = supabase.table('trocas_cartucho').select('id', count='exact').eq('usuario_id', user_id).execute()  # Conta logs relacionados.
                                if response.count > 0:  # Se houver logs,
                                    st.session_state.deleting_sector_id, st.session_state.deleting_sector_name, st.session_state.deleting_sector_logs_count = user_id, user_name, response.count  # Define estados para deleção.
                                    st.rerun()  # Recarrega.
                                else:  # Sem logs,
                                    try:  # Tenta deletar diretamente.
                                        supabase.table('usuarios').delete().eq('id', user_id).execute()  # Deleta setor.
                                        st.success(f"Setor '{user_name}' removido com sucesso!")  # Sucesso.
                                        st.rerun()  # Recarrega.
                                    except Exception as e:  # Erro.
                                        st.error(f"Ocorreu um erro ao remover '{user_name}': {e}")

    # --- PÁGINA: GERENCIAR EQUIPAMENTOS ---
    elif page == "Gerenciar Equipamentos":  # Verifica página "Gerenciar Equipamentos".
        st.header("Gerenciar Equipamentos")  # Cabeçalho.
        if 'deleting_equip_id' not in st.session_state:  # Inicializa estados para deleção de equipamento.
            st.session_state.deleting_equip_id, st.session_state.deleting_equip_model, st.session_state.deleting_equip_logs_count = None, None, 0
        if st.session_state.deleting_equip_id is not None:  # Se deletando,
            st.warning(f"⚠️ **ATENÇÃO:** Você está prestes a apagar o equipamento **'{st.session_state.deleting_equip_model}'** e todos os seus **{st.session_state.deleting_equip_logs_count}** registros de troca. Esta ação é irreversível.")  # Aviso.
            with st.form("confirm_delete_equip_form"):  # Formulário.
                password = st.text_input("Para confirmar, digite a senha de exclusão:", type="password")  # Senha.
                col_confirm, col_cancel = st.columns(2)  # Colunas.
                with col_confirm:  # Confirmação,
                    if st.form_submit_button("Confirmar Exclusão Permanente", type="primary"):  # Botão.
                        if password == st.secrets["auth"].get("delete_password", st.secrets["auth"]["password"]):  # Verifica.
                            try:  # Tenta.
                                supabase.table('trocas_cartucho').delete().eq('equipamento_id', st.session_state.deleting_equip_id).execute()  # Deleta logs.
                                supabase.table('equipamentos').delete().eq('id', st.session_state.deleting_equip_id).execute()  # Deleta equipamento.
                                st.success(f"O equipamento '{st.session_state.deleting_equip_model}' e seus registros foram removidos com sucesso!")  # Sucesso.
                                st.session_state.deleting_equip_id = None  # Reseta.
                                st.rerun()  # Recarrega.
                            except Exception as e:  # Erro.
                                st.error(f"Ocorreu um erro durante a exclusão: {e}")
                        else:  # Senha errada.
                            st.error("Senha de exclusão incorreta.")
                with col_cancel:  # Cancelar,
                    if st.form_submit_button("Cancelar"):  # Botão.
                        st.session_state.deleting_equip_id = None  # Reseta.
                        st.rerun()  # Recarrega.
        else:  # Não deletando,
            with st.expander("Adicionar Novo Equipamento"):  # Expander para adicionar.
                users_data = get_users()  # Obtém setores.
                if not users_data:  # Se vazio,
                    st.warning("Você precisa cadastrar um setor antes de poder adicionar um equipamento.")  # Aviso.
                else:  # Caso contrário,
                    setor_map = {user['name']: user['id'] for user in users_data}  # Mapa de setores.
                    with st.form("novo_equipamento_form", clear_on_submit=True):  # Formulário.
                        modelo_equipamento = st.text_input("Modelo do Equipamento (ex: HP LaserJet Pro M404n):")  # Input modelo.
                        categoria_equipamento = st.selectbox("Categoria do Suprimento:", ["Cartucho de Tinta", "Suprimento Laser"])  # Selectbox categoria.
                        setor_selecionado = st.selectbox("Associar ao Setor:", options=setor_map.keys())  # Selectbox setor.
                        if st.form_submit_button("Adicionar Equipamento"):  # Botão.
                            if modelo_equipamento and setor_selecionado and categoria_equipamento:  # Se preenchido,
                                setor_id = setor_map[setor_selecionado]  # Obtém ID.
                                try:  # Tenta inserir.
                                    supabase.table('equipamentos').insert({'modelo': modelo_equipamento, 'setor_id': setor_id, 'categoria': categoria_equipamento}).execute()  # Insere.
                                    st.success(f"Equipamento '{modelo_equipamento}' adicionado com sucesso!")  # Sucesso.
                                    st.rerun()  # Recarrega.
                                except Exception as e:  # Erro.
                                    st.error(f"Ocorreu um erro ao adicionar o equipamento: {e}")
                            else:  # Não preenchido.
                                st.error("Por favor, preencha todos os campos.")
            st.markdown("---")  # Linha.
            st.subheader("Lista de Equipamentos Cadastrados")  # Subcabeçalho.
            equipamentos_data = get_equipamentos()  # Obtém equipamentos.
            if not equipamentos_data:  # Vazio,
                st.info("Nenhum equipamento cadastrado.")  # Info.
            else:  # Caso contrário,
                for item in equipamentos_data:  # Itera.
                    with st.container(border=True):  # Container.
                        equip_id, equip_model, equip_category = item['id'], item['modelo'], item.get('categoria', 'N/A')  # Extrai dados.
                        sector_name = item['usuarios']['name'] if item.get('usuarios') else "N/A"  # Nome do setor.
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])  # Colunas.
                        col1.text(equip_model)  # Modelo.
                        col2.text(equip_category)  # Categoria.
                        col3.text(sector_name)  # Setor.
                        if col4.button("🗑️", key=f"del_equip_{equip_id}", help="Remover este equipamento"):  # Botão deletar.
                            response = supabase.table('trocas_cartucho').select('id', count='exact').eq('equipamento_id', equip_id).execute()  # Conta logs.
                            if response.count > 0:  # Se houver,
                                st.session_state.deleting_equip_id, st.session_state.deleting_equip_model, st.session_state.deleting_equip_logs_count = equip_id, equip_model, response.count  # Define estados.
                                st.rerun()  # Recarrega.
                            else:  # Sem logs,
                                try:  # Deleta diretamente.
                                    supabase.table('equipamentos').delete().eq('id', equip_id).execute()  # Deleta.
                                    st.success(f"Equipamento '{equip_model}' removido com sucesso!")  # Sucesso.
                                    st.rerun()  # Recarrega.
                                except Exception as e:  # Erro.
                                    st.error(f"Ocorreu um erro ao remover o equipamento: {e}")

    # --- PÁGINA: GERENCIAR SUPRIMENTOS ---
    elif page == "Gerenciar Suprimentos":  # Verifica página "Gerenciar Suprimentos".
        st.header("Gerenciar Suprimentos (Catálogo)")  # Cabeçalho.
        if 'deleting_suprimento_id' not in st.session_state:  # Inicializa estados para deleção.
            st.session_state.deleting_suprimento_id = None
            st.session_state.deleting_suprimento_modelo = None
            st.session_state.deleting_suprimento_logs_count = 0
        if st.session_state.deleting_suprimento_id is not None:  # Se deletando,
            st.warning(f"⚠️ **ATENÇÃO:** Você está prestes a apagar o suprimento **'{st.session_state.deleting_suprimento_modelo}'** e todos os seus **{st.session_state.deleting_suprimento_logs_count}** registros de troca. Esta ação é irreversível.")  # Aviso.
            with st.form("confirm_delete_suprimento_form"):  # Formulário.
                password = st.text_input("Para confirmar, digite a senha de exclusão:", type="password")  # Senha.
                col_confirm, col_cancel = st.columns(2)  # Colunas.
                with col_confirm:  # Confirmação,
                    if st.form_submit_button("Confirmar Exclusão Permanente", type="primary"):  # Botão.
                        correct_password = st.secrets["auth"].get("delete_password", st.secrets["auth"]["password"])  # Obtém senha correta.
                        if password == correct_password:  # Verifica.
                            try:  # Tenta.
                                supabase.table('trocas_cartucho').delete().eq('suprimento_id', st.session_state.deleting_suprimento_id).execute()  # Deleta logs.
                                supabase.table('suprimentos').delete().eq('id', st.session_state.deleting_suprimento_id).execute()  # Deleta suprimento.
                                st.success(f"O suprimento '{st.session_state.deleting_suprimento_modelo}' e seus registros foram removidos com sucesso!")  # Sucesso.
                                st.session_state.deleting_suprimento_id = None  # Reseta.
                                st.rerun()  # Recarrega.
                            except Exception as e:  # Erro.
                                st.error(f"Ocorreu um erro durante a exclusão: {e}")
                        else:  # Errada.
                            st.error("Senha de exclusão incorreta.")
                with col_cancel:  # Cancelar,
                    if st.form_submit_button("Cancelar"):  # Botão.
                        st.session_state.deleting_suprimento_id = None  # Reseta.
                        st.rerun()  # Recarrega.
        else:  # Não deletando,
            with st.expander("Adicionar Novo Suprimento ao Catálogo"):  # Expander.
                st.write("Preencha os detalhes do novo modelo de suprimento.")  # Instrução.

                modelo = st.text_input("Modelo (ex: HP 664, Brother TN-1060)", key='new_suprimento_modelo')  # Input modelo.
                OPCAO_TINTA = "Cartucho de Tinta"  # Opção tinta.
                OPCAO_LASER = "Suprimento Laser"  # Opção laser.

                categoria = st.selectbox(  # Selectbox categoria.
                    "Categoria",
                    [OPCAO_TINTA, OPCAO_LASER],
                    key='new_suprimento_categoria'
                )
                tipo = None  # Inicializa tipo.

                if categoria == OPCAO_TINTA:  # Se tinta,
                    tipo = st.selectbox("Tipo", ["Preto", "Colorido"], key='new_suprimento_tipo_tinta')  # Selectbox tipo tinta.
                elif categoria == OPCAO_LASER:  # Se laser,
                    tipo = st.selectbox("Tipo", ["Toner", "Cilindro"], key='new_suprimento_tipo_laser')  # Selectbox tipo laser.
                if st.button("Adicionar Suprimento"):  # Botão adicionar.
                    if modelo and categoria and tipo:  # Se preenchido,
                        try:  # Tenta inserir.
                            supabase.table('suprimentos').insert({
                                'modelo': modelo,
                                'categoria': categoria,
                                'tipo': tipo
                            }).execute()  # Insere.
                            st.success(f"Suprimento '{modelo}' adicionado ao catálogo!")  # Sucesso.
                            if 'new_suprimento_modelo' in st.session_state:  # Limpa estados.
                                del st.session_state['new_suprimento_modelo']
                            if 'new_suprimento_categoria' in st.session_state:
                                del st.session_state['new_suprimento_categoria']
                            if 'new_suprimento_tipo_tinta' in st.session_state:
                                del st.session_state['new_suprimento_tipo_tinta']
                            if 'new_suprimento_tipo_laser' in st.session_state:
                                del st.session_state['new_suprimento_tipo_laser']
                            st.rerun()  # Recarrega.
                        except Exception as e:  # Erro.
                            st.error(f"Ocorreu um erro: {e}")
                    else:  # Não preenchido.
                        st.error("Por favor, preencha todos os campos.")

            st.markdown("---")  # Linha.
            st.subheader("Catálogo de Suprimentos Cadastrados")  # Subcabeçalho.

            suprimentos_data = get_suprimentos()  # Obtém suprimentos.
            if not suprimentos_data:  # Vazio,
                st.info("Nenhum suprimento cadastrado.")  # Info.
            else:  # Caso contrário,
                header_cols = st.columns([3, 2, 2, 1])  # Colunas cabeçalho.
                header_cols[0].write("**Modelo**")  # Modelo.
                header_cols[1].write("**Categoria**")  # Categoria.
                header_cols[2].write("**Tipo**")  # Tipo.
                header_cols[3].write("**Ação**")  # Ação.
                st.markdown("<hr style='margin-top: -0.5em; margin-bottom: 0.5em;'>", unsafe_allow_html=True)  # Linha.

                for item in suprimentos_data:  # Itera.
                    sup_id, sup_model, sup_category, sup_type = item['id'], item['modelo'], item.get('categoria', 'N/A'), item.get('tipo', 'N/A')  # Extrai.

                    with st.container():  # Container.
                        row_cols = st.columns([3, 2, 2, 1])  # Colunas linha.
                        row_cols[0].text(sup_model)  # Modelo.
                        row_cols[1].text(sup_category)  # Categoria.
                        row_cols[2].text(sup_type)  # Tipo.

                        if row_cols[3].button("🗑️", key=f"del_sup_{sup_id}", help=f"Remover '{sup_model}'"):  # Botão deletar.
                            response = supabase.table('trocas_cartucho').select('id', count='exact').eq('suprimento_id', sup_id).execute()  # Conta logs.

                            if response.count > 0:  # Se houver,
                                st.session_state.deleting_suprimento_id = sup_id  # Define estados.
                                st.session_state.deleting_suprimento_modelo = sup_model
                                st.session_state.deleting_suprimento_logs_count = response.count
                                st.rerun()  # Recarrega.
                            else:  # Sem,
                                try:  # Deleta.
                                    supabase.table('suprimentos').delete().eq('id', sup_id).execute()  # Deleta.
                                    st.success(f"Suprimento '{sup_model}' removido com sucesso!")  # Sucesso.
                                    st.rerun()  # Recarrega.
                                except Exception as e:  # Erro.
                                    st.error(f"Ocorreu um erro ao remover o suprimento: {e}")
# --- LÓGICA PRINCIPAL DE EXECUÇÃO ---
run_app()  # Chama a função principal para executar a app.
