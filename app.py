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
        # Usa a senha de login principal
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
        for key in list(st.session_state.keys()):
            if key != 'password_correct':
                del st.session_state[key]
        st.rerun()

    st.title("🖨️ Gerenciador de Suprimentos de Impressão")
    st.markdown("---")

    page = st.sidebar.radio("Selecione uma página", ["Registrar Troca", "Dashboard de Análise", "Gerenciar Setores"])

    # --- PÁGINA: REGISTRAR TROCA ---
    if page == "Registrar Troca":
        # (Esta página não foi alterada)
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
                tipos_a_registrar = st.multiselect("2. Marque o(s) tipo(s) trocado(s):", opcoes_tipo, placeholder="Selecione as opções")
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
                                supabase.table('trocas_cartucho').insert({'usuario_id': user_id, 'data_troca': formatted_date, 'categoria': categoria_selecionada, 'tipo': tipo}).execute()
                                sucessos += 1
                            except Exception as e:
                                erros.append(f"Falha ao registrar '{tipo}': {e}")
                        if sucessos > 0: st.success(f"{sucessos} registro(s) criado(s) com sucesso para {selected_user_name}!")
                        if erros: 
                            for erro in erros: st.error(erro)

    # --- PÁGINA: DASHBOARD DE ANÁLISE (MODIFICADA) ---
    elif page == "Dashboard de Análise":
        st.header("Dashboard de Análise de Trocas")
        
        if 'sort_by' not in st.session_state:
            st.session_state.sort_by = 'Data'
            st.session_state.sort_ascending = False
        if 'deleting_log_id' not in st.session_state:
            st.session_state.deleting_log_id = None

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
            
            st.sidebar.markdown("---"); st.sidebar.header("Filtros do Dashboard")
            categorias_filtro = ["Todas"] + df[df['Categoria'] != 'Não definida']['Categoria'].unique().tolist()
            categoria_filtrada = st.sidebar.selectbox("Filtrar por Categoria:", categorias_filtro)
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            lista_meses = ["Todos"] + sorted(df['AnoMês'].unique(), reverse=True)
            mes_selecionado = st.sidebar.selectbox("Filtrar por Mês/Ano:", options=lista_meses)
            
            df_filtrado = df.copy()
            if categoria_filtrada != "Todas":
                df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_filtrada]
            if mes_selecionado != "Todos":
                df_filtrado = df_filtrado[df_filtrado['AnoMês'] == mes_selecionado]
            
            st.markdown("### Gráficos de Análise")
            
            if df_filtrado.empty:
                st.warning("Nenhum registro encontrado para os filtros selecionados.")
            else:
                # (Gráficos)
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Total de Trocas por Setor")
                    # ... código do gráfico de barras
                with col2:
                    st.subheader("Proporção por Tipo de Suprimento")
                    # ... código do gráfico de pizza
                st.subheader("Trocas ao Longo do Tempo")
                # ... código do gráfico de linha
            
            st.markdown("---")
            titulo_historico = f"Histórico de Trocas ({categoria_filtrada}, {mes_selecionado})"
            st.subheader(titulo_historico)

            # MUDANÇA: LÓGICA DE CONFIRMAÇÃO AGORA PEDE SENHA
            if st.session_state.deleting_log_id is not None:
                log_details = df[df['ID Troca'] == st.session_state.deleting_log_id].iloc[0]
                
                st.warning(f"Você tem certeza que deseja apagar o registro abaixo?")
                st.write(f"**Data:** {log_details['Data'].strftime('%d/%m/%Y')}, **Setor:** {log_details['Setor']}, **Tipo:** {log_details['Tipo']}")

                with st.form("confirm_delete_log_form"):
                    password = st.text_input("Para confirmar, digite a senha de exclusão:", type="password")
                    
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.form_submit_button("Sim, apagar registro", type="primary"):
                            # Usa a senha de exclusão
                            if password == st.secrets["auth"]["delete_password"]:
                                try:
                                    supabase.table('trocas_cartucho').delete().eq('id', st.session_state.deleting_log_id).execute()
                                    st.success("Registro apagado com sucesso!")
                                    st.session_state.deleting_log_id = None
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Ocorreu um erro ao apagar o registro: {e}")
                            else:
                                st.error("Senha de exclusão incorreta.")
                    
                    with col_cancel:
                        if st.form_submit_button("Cancelar"):
                            st.session_state.deleting_log_id = None
                            st.rerun()

            # TABELA INTERATIVA
            def set_sort_order(column_name):
                if st.session_state.sort_by == column_name:
                    st.session_state.sort_ascending = not st.session_state.sort_ascending
                else:
                    st.session_state.sort_by = column_name
                    st.session_state.sort_ascending = True
                st.session_state.deleting_log_id = None

            df_sorted = df_filtrado.sort_values(by=st.session_state.sort_by, ascending=st.session_state.sort_ascending)

            header_cols = st.columns([2, 3, 2, 2, 1])
            if header_cols[0].button('Data'): set_sort_order('Data')
            if header_cols[1].button('Setor'): set_sort_order('Setor')
            if header_cols[2].button('Categoria'): set_sort_order('Categoria')
            if header_cols[3].button('Tipo'): set_sort_order('Tipo')
            header_cols[4].write("**Ação**")

            st.markdown("<hr style='margin-top: -0.5em; margin-bottom: 0.5em;'>", unsafe_allow_html=True)

            for index, row in df_sorted.iterrows():
                row_cols = st.columns([2, 3, 2, 2, 1])
                row_cols[0].text(row['Data'].strftime('%d/%m/%Y'))
                row_cols[1].text(row['Setor'])
                row_cols[2].text(row['Categoria'])
                row_cols[3].text(row['Tipo'])
                
                if row_cols[4].button("🗑️", key=f"del_log_{row['ID Troca']}", help="Remover este registro"):
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
                password = st.text_input("Para confirmar, digite a senha de exclusão:", type="password")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.form_submit_button("Confirmar Exclusão Permanente", type="primary"):
                        # Usa a senha de exclusão
                        if password == st.secrets["auth"]["delete_password"]:
                            try:
                                supabase.table('trocas_cartucho').delete().eq('usuario_id', st.session_state.deleting_sector_id).execute()
                                supabase.table('usuarios').delete().eq('id', st.session_state.deleting_sector_id).execute()
                                st.success(f"O setor '{st.session_state.deleting_sector_name}' e seus registros foram removidos com sucesso!")
                                st.session_state.deleting_sector_id = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Ocorreu um erro durante a exclusão: {e}")
                        else:
                            st.error("Senha de exclusão incorreta. A ação não foi realizada.")
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
