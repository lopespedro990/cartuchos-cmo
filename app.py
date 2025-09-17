import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA E SUPABASE ---
st.set_page_config(layout="wide", page_title="Gerenciador de Suprimentos")

@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNÇÃO DE LOGIN ---
def show_login_form():
    st.title("🔐 Acesso Restrito")
    password = st.text_input("Digite a senha para acessar:", type="password", key="password")

    if st.button("Entrar"):
        if password == st.secrets["auth"]["password"]:
            st.session_state['password_correct'] = True
            del st.session_state['password'] 
            st.rerun()
        else:
            st.error("Senha incorreta.")

# --- FUNÇÕES DA APLICAÇÃO ---
def get_users():
    response = supabase.table('usuarios').select('id, name').order('name').execute()
    return response.data

def get_change_logs():
    response = supabase.table('trocas_cartucho').select('*, usuarios(name)').order('data_troca', desc=True).execute()
    return response.data

# --- APLICAÇÃO PRINCIPAL ---
def run_app():
    logo_url = "https://www.camaraourinhos.sp.gov.br/img/customizacao/cliente/facebook/imagem_compartilhamento_redes.jpg"
    st.sidebar.image(logo_url, use_container_width=True)

    if st.sidebar.button("Sair"):
        st.session_state['password_correct'] = False
        # Limpa todos os estados de sessão ao sair
        for key in list(st.session_state.keys()):
            if key != 'password_correct':
                del st.session_state[key]
        st.rerun()

    st.title("🖨️ Gerenciador de Suprimentos de Impressão")
    st.markdown("---")

    page = st.sidebar.radio("Selecione uma página", ["Registrar Troca", "Dashboard de Análise", "Gerenciar Setores"])

    # --- PÁGINA: REGISTRAR TROCA ---
    if page == "Registrar Troca":
        st.header("Registrar uma Nova Troca de Suprimento")
        users = get_users()
        user_names = {user['name']: user['id'] for user in users}

        if not users:
            st.warning("Nenhum setor cadastrado.")
        else:
            categorias = ["Cartucho de Tinta", "Suprimento Laser"]
            categoria_selecionada = st.selectbox("1. Selecione a Categoria do Suprimento:", categorias)

            if categoria_selecionada == "Cartucho de Tinta":
                opcoes_tipo = ["Preto", "Colorido"]
            else:
                opcoes_tipo = ["Toner", "Cilindro"]

            with st.form("registro_troca_form"):
                selected_user_name = st.selectbox("Selecione o Setor:", options=user_names.keys())
                
                tipos_a_registrar = st.multiselect(
                    "2. Marque o(s) tipo(s) trocado(s):", 
                    opcoes_tipo,
                    placeholder="Selecione as opções"
                )
                
                change_date = st.date_input("3. Data da Troca:", datetime.now())
                
                if st.form_submit_button("Registrar Troca"):
                    if not tipos_a_registrar:
                        st.error("Por favor, selecione pelo menos um tipo de suprimento.")
                    else:
                        user_id = user_names[selected_user_name]
                        formatted_date = change_date.strftime("%Y-%m-%d")
                        sucessos, erros = 0, []
                        
                        for tipo in tipos_a_registrar:
                            try:
                                supabase.table('trocas_cartucho').insert({
                                    'usuario_id': user_id, 
                                    'data_troca': formatted_date,
                                    'categoria': categoria_selecionada,
                                    'tipo': tipo
                                }).execute()
                                sucessos += 1
                            except Exception as e:
                                erros.append(f"Falha ao registrar '{tipo}': {e}")

                        if sucessos > 0: st.success(f"{sucessos} registro(s) criado(s) com sucesso para {selected_user_name}!")
                        if erros: 
                            for erro in erros: st.error(erro)

    # --- PÁGINA: DASHBOARD DE ANÁLISE (MODIFICADA) ---
    elif page == "Dashboard de Análise":
        st.header("Dashboard de Análise de Trocas")
        logs = get_change_logs()
        if not logs:
            st.info("Ainda não há registros de troca para exibir.")
        else:
            processed_logs = []
            for log in logs:
                processed_logs.append({
                    'ID Troca': log['id'], 'Data': log['data_troca'],
                    'Setor': log.get('usuarios', {}).get('name', 'Setor Desconhecido'),
                    'Categoria': log.get('categoria', 'Não definida'),
                    'Tipo': log.get('tipo', 'Não definido')
                })
            
            df = pd.DataFrame(processed_logs)
            df['Data'] = pd.to_datetime(df['Data'])
            df = df.sort_values(by='Data', ascending=False)

            st.sidebar.markdown("---")
            st.sidebar.header("Filtros do Dashboard")
            
            categorias_filtro = ["Todas"] + df[df['Categoria'] != 'Não definida']['Categoria'].unique().tolist()
            categoria_filtrada = st.sidebar.selectbox("Filtrar por Categoria:", categorias_filtro)
            
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            lista_meses = ["Todos"] + sorted(df['AnoMês'].unique(), reverse=True)
            mes_selecionado = st.sidebar.selectbox("Filtrar por Mês/Ano:", options=lista_meses)
            
            df_filtrado = df
            if categoria_filtrada != "Todas":
                df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_filtrada]
            if mes_selecionado != "Todos":
                df_filtrado = df_filtrado[df_filtrado['AnoMês'] == mes_selecionado]
            
            st.markdown("### Gráficos de Análise")
            
            if df_filtrado.empty:
                st.warning("Nenhum registro encontrado para os filtros selecionados.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Total de Trocas por Setor")
                    user_counts = df_filtrado['Setor'].value_counts().reset_index()
                    user_counts.columns = ['Setor', 'Total de Trocas']
                    titulo_grafico_bar = f"Setores que mais trocaram ({categoria_filtrada}, {mes_selecionado})"
                    fig_bar = px.bar(user_counts, x='Setor', y='Total de Trocas', title=titulo_grafico_bar, labels={'Setor': 'Nome do Setor', 'Total de Trocas': 'Quantidade'}, text='Total de Trocas')
                    fig_bar.update_traces(textposition='outside'); st.plotly_chart(fig_bar, use_container_width=True)

                with col2:
                    st.subheader("Proporção por Tipo de Suprimento")
                    type_counts = df_filtrado['Tipo'].value_counts().reset_index()
                    type_counts.columns = ['Tipo', 'Quantidade']
                    titulo_grafico_pie = f"Proporção ({categoria_filtrada}, {mes_selecionado})"
                    fig_pie = px.pie(type_counts, names='Tipo', values='Quantidade', title=titulo_grafico_pie, hole=.3)
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.subheader("Trocas ao Longo do Tempo")
                monthly_changes = df_filtrado.groupby('AnoMês').size().reset_index(name='Quantidade')
                titulo_grafico_linha = f"Volume de Trocas por Mês ({categoria_filtrada})"
                fig_line = px.line(monthly_changes.sort_values(by='AnoMês'), x='AnoMês', y='Quantidade', title=titulo_grafico_linha, markers=True, labels={'AnoMês': 'Mês/Ano', 'Quantidade': 'Nº de Trocas'})
                st.plotly_chart(fig_line, use_container_width=True)
                
            st.markdown("---")
            titulo_historico = f"Histórico de Trocas ({categoria_filtrada}, {mes_selecionado})"
            st.subheader(titulo_historico)

            # LÓGICA DE CONFIRMAÇÃO DE EXCLUSÃO DE REGISTRO
            if 'deleting_log_id' not in st.session_state:
                st.session_state.deleting_log_id = None

            if st.session_state.deleting_log_id is not None:
                # Encontra os detalhes do registro a ser excluído para mostrar na mensagem
                log_details = df_filtrado[df_filtrado['ID Troca'] == st.session_state.deleting_log_id].iloc[0]
                
                st.warning(f"Você tem certeza que deseja apagar o registro abaixo?")
                st.write(f"**Data:** {log_details['Data'].strftime('%d/%m/%Y')}, **Setor:** {log_details['Setor']}, **Tipo:** {log_details['Tipo']}")

                col_confirm, col_cancel = st.columns(2)
                if col_confirm.button("Sim, apagar registro", type="primary"):
                    try:
                        supabase.table('trocas_cartucho').delete().eq('id', st.session_state.deleting_log_id).execute()
                        st.success("Registro apagado com sucesso!")
                        st.session_state.deleting_log_id = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao apagar o registro: {e}")
                
                if col_cancel.button("Cancelar"):
                    st.session_state.deleting_log_id = None
                    st.rerun()

            # CONSTRUÇÃO DA TABELA DE HISTÓRICO COM BOTÕES
            # Cabeçalho da tabela
            header_cols = st.columns([2, 3, 2, 2, 1])
            header_cols[0].write("**Data**")
            header_cols[1].write("**Setor**")
            header_cols[2].write("**Categoria**")
            header_cols[3].write("**Tipo**")
            
            # Linhas da tabela
            for index, row in df_filtrado.iterrows():
                with st.container(border=True):
                    row_cols = st.columns([2, 3, 2, 2, 1])
                    row_cols[0].text(row['Data'].strftime('%d/%m/%Y'))
                    row_cols[1].text(row['Setor'])
                    row_cols[2].text(row['Categoria'])
                    row_cols[3].text(row['Tipo'])
                    
                    # Botão para iniciar o processo de exclusão
                    if row_cols[4].button("Remover", key=f"del_log_{row['ID Troca']}"):
                        st.session_state.deleting_log_id = row['ID Troca']
                        st.rerun()

    # --- PÁGINA: GERENCIAR SETORES ---
    elif page == "Gerenciar Setores":
        st.header("Gerenciar Setores")
        if 'deleting_sector_id' not in st.session_state:
            st.session_state.deleting_sector_id, st.session_state.deleting_sector_name, st.session_state.deleting_sector_logs_count = None, None, 0

        if st.session_state.deleting_sector_id is not None:
            st.warning(f"⚠️ **ATENÇÃO:** Você está prestes a apagar o setor **'{st.session_state.deleting_sector_name}'** e todos os seus **{st.session_state.deleting_sector_logs_count}** registros. Esta ação é irreversível.")
            with st.form("confirm_delete_form"):
                password = st.text_input("Para confirmar, digite a senha de administrador:", type="password")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.form_submit_button("Confirmar Exclusão Permanente", type="primary"):
                        if password == st.secrets["auth"]["password"]:
                            try:
                                supabase.table('trocas_cartucho').delete().eq('usuario_id', st.session_state.deleting_sector_id).execute()
                                supabase.table('usuarios').delete().eq('id', st.session_state.deleting_sector_id).execute()
                                st.success(f"O setor '{st.session_state.deleting_sector_name}' e seus registros foram removidos com sucesso!")
                                st.session_state.deleting_sector_id = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Ocorreu um erro durante a exclusão: {e}")
                        else:
                            st.error("Senha incorreta. A exclusão não foi realizada.")
                with col_cancel:
                    if st.form_submit_button("Cancelar"):
                        st.session_state.deleting_sector_id = None
                        st.rerun()
        else:
            with st.expander("Adicionar Novo Setor"):
                with st.form("novo_setor_form", clear_on_submit=True):
                    new_user_name = st.text_input("Nome do Novo Setor:")
                    if st.form_submit_button("Adicionar Setor"):
                        if new_user_name:
                            try:
                                supabase.table('usuarios').insert({'name': new_user_name}).execute()
                                st.success(f"Setor '{new_user_name}' adicionado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Ocorreu um erro: {e}")
            st.markdown("---")
            st.subheader("Lista de Setores Cadastrados")
            users_data = get_users()
            if not users_data:
                st.info("Nenhum setor cadastrado.")
            else:
                for user in users_data:
                    with st.container(border=True):
                        user_id, user_name = user['id'], user['name']
                        col1, col2 = st.columns([4, 1])
                        col1.markdown(f"<p style='margin-top: 5px; font-size: 1.1em;'>{user_name}</p>", unsafe_allow_html=True)
                        if col2.button("Remover", key=f"delete_{user_id}", type="primary"):
                            response = supabase.table('trocas_cartucho').select('id', count='exact').eq('usuario_id', user_id).execute()
                            if response.count > 0:
                                st.session_state.deleting_sector_id, st.session_state.deleting_sector_name, st.session_state.deleting_sector_logs_count = user_id, user_name, response.count
                                st.rerun()
                            else:
                                try:
                                    supabase.table('usuarios').delete().eq('id', user_id).execute()
                                    st.success(f"Setor '{user_name}' removido com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Ocorreu um erro ao remover '{user_name}': {e}")

# --- LÓGICA PRINCIPAL DE EXECUÇÃO ---
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False

if st.session_state['password_correct']:
    run_app()
else:
    show_login_form()
