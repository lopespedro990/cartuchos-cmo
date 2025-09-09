import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA E SUPABASE ---
st.set_page_config(layout="wide", page_title="Gerenciador de Cartuchos")

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
    # O select('*') já vai pegar a nova coluna 'tipo_cartucho' automaticamente
    response = supabase.table('trocas_cartucho').select('*, usuarios(name)').order('data_troca', desc=True).execute()
    return response.data

# --- APLICAÇÃO PRINCIPAL ---
def run_app():
    st.sidebar.title(f"Bem-vindo!")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state['password_correct'] = False
        st.rerun()

    st.title("🖨️ Gerenciador de Troca de Cartuchos")
    st.markdown("---")

    page = st.sidebar.radio("Selecione uma página", ["Registrar Troca", "Dashboard de Análise", "Gerenciar Setores"])

    # --- PÁGINA: REGISTRAR TROCA ---
    if page == "Registrar Troca":
        st.header("Registrar uma Nova Troca de Cartucho")
        users = get_users()
        user_names = {user['name']: user['id'] for user in users}

        if not users:
            st.warning("Nenhum setor cadastrado. Adicione um na página 'Gerenciar Setores'.")
        else:
            with st.form("registro_troca_form"):
                selected_user_name = st.selectbox("Selecione o Setor:", options=user_names.keys())
                
                # NOVO CAMPO PARA SELECIONAR O TIPO DO CARTUCHO
                cartridge_type = st.radio("Tipo do Cartucho:", ("Preto", "Colorido"), horizontal=True)
                
                change_date = st.date_input("Data da Troca:", datetime.now())
                
                if st.form_submit_button("Registrar Troca"):
                    user_id = user_names[selected_user_name]
                    formatted_date = change_date.strftime("%Y-%m-%d")
                    try:
                        # DADO DO NOVO CAMPO É INSERIDO AQUI
                        supabase.table('trocas_cartucho').insert({
                            'usuario_id': user_id, 
                            'data_troca': formatted_date,
                            'tipo_cartucho': cartridge_type
                        }).execute()
                        st.success(f"Troca de cartucho {cartridge_type.lower()} registrada para {selected_user_name}!")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

    # --- PÁGINA: DASHBOARD DE ANÁLISE ---
    elif page == "Dashboard de Análise":
        st.header("Dashboard de Análise de Trocas")
        logs = get_change_logs()
        if not logs:
            st.info("Ainda não há registros de troca para exibir.")
        else:
            processed_logs = []
            for log in logs:
                processed_logs.append({
                    'ID Troca': log['id'],
                    'Data': log['data_troca'],
                    'Setor': log.get('usuarios', {}).get('name', 'Setor Desconhecido'),
                    # NOVA INFORMAÇÃO SENDO PROCESSADA
                    'Tipo': log.get('tipo_cartucho', 'Não especificado')
                })
            
            df = pd.DataFrame(processed_logs)
            df['Data'] = pd.to_datetime(df['Data'])
            df = df.sort_values(by='Data', ascending=False)

            st.sidebar.markdown("---")
            st.sidebar.header("Filtros do Dashboard")
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            lista_meses = sorted(df['AnoMês'].unique(), reverse=True)
            lista_meses.insert(0, "Todos")
            mes_selecionado = st.sidebar.selectbox("Filtrar por Mês/Ano:", options=lista_meses)
            
            df_filtrado = df if mes_selecionado == "Todos" else df[df['AnoMês'] == mes_selecionado]
            
            st.markdown("### Gráficos de Análise")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Total de Trocas por Setor")
                if not df_filtrado.empty:
                    user_counts = df_filtrado['Setor'].value_counts().reset_index()
                    user_counts.columns = ['Setor', 'Total de Trocas']
                    titulo_grafico_bar = f"Setores que mais trocaram em {mes_selecionado}" if mes_selecionado != "Todos" else "Setores que mais trocam (Geral)"
                    fig_bar = px.bar(user_counts, x='Setor', y='Total de Trocas', title=titulo_grafico_bar, labels={'Setor': 'Nome do Setor', 'Total de Trocas': 'Quantidade'}, text='Total de Trocas')
                    fig_bar.update_traces(textposition='outside')
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.warning("Nenhum registro para o período selecionado.")

            # NOVO GRÁFICO DE PIZZA
            with col2:
                st.subheader("Proporção Preto vs. Colorido")
                if not df_filtrado.empty:
                    type_counts = df_filtrado['Tipo'].value_counts().reset_index()
                    type_counts.columns = ['Tipo', 'Quantidade']
                    titulo_grafico_pie = f"Proporção em {mes_selecionado}" if mes_selecionado != "Todos" else "Proporção Geral"
                    fig_pie = px.pie(type_counts, names='Tipo', values='Quantidade', title=titulo_grafico_pie, hole=.3)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.write("") # Espaço vazio se não houver dados

            # Gráfico de linha movido para baixo para melhor layout
            st.subheader("Trocas ao Longo do Tempo")
            monthly_changes = df.groupby('AnoMês').size().reset_index(name='Quantidade')
            fig_line = px.line(monthly_changes.sort_values(by='AnoMês'), x='AnoMês', y='Quantidade', title="Volume de Trocas por Mês", markers=True, labels={'AnoMês': 'Mês/Ano', 'Quantidade': 'Nº de Trocas'})
            st.plotly_chart(fig_line, use_container_width=True)
            
            st.markdown("---")
            titulo_historico = f"Histórico de Trocas para {mes_selecionado}" if mes_selecionado != "Todos" else "Histórico Completo de Trocas"
            st.subheader(titulo_historico)
            # TABELA DE HISTÓRICO ATUALIZADA
            st.dataframe(df_filtrado[['Data', 'Setor', 'Tipo']].reset_index(drop=True), use_container_width=True)

    # --- PÁGINA: GERENCIAR SETORES ---
    elif page == "Gerenciar Setores":
        # (Esta página não precisa de alterações)
        st.header("Gerenciar Setores")
        with st.form("novo_usuario_form"):
            new_user_name = st.text_input("Nome do Novo Setor:")
            if st.form_submit_button("Adicionar Setor"):
                if new_user_name:
                    try:
                        supabase.table('usuarios').insert({'name': new_user_name}).execute()
                        st.success(f"Setor '{new_user_name}' adicionado!")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")
        
        st.markdown("---")
        st.subheader("Lista de Setores Cadastrados")
        users_data = get_users()
        if users_data:
            df_users = pd.DataFrame(users_data)[['name']].rename(columns={'name': 'Nome do Setor'})
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("Nenhum setor cadastrado.")


# --- LÓGICA PRINCIPAL DE EXECUÇÃO ---
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False

if st.session_state['password_correct']:
    run_app()
else:
    show_login_form()