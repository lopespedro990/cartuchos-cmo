import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA E SUPABASE ---
st.set_page_config(layout="wide", page_title="Gerenciador de Troca de Cartuchos")

@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNÇÃO DE LOGIN ---
def check_password():
    """Retorna True se a senha estiver correta, False caso contrário."""
    st.title("🔐 Acesso Restrito")
    password = st.text_input("Digite a senha para acessar:", type="password")

    # Verifica se a senha digitada é a mesma que está nos Secrets
    if password == st.secrets["auth"]["password"]:
        return True
    elif password:  # Se o usuário digitou algo, mas está incorreto
        st.error("Senha incorreta.")
        return False
    else:  # Se o campo está vazio
        return False

# --- FUNÇÕES DA APLICAÇÃO ---
def get_users():
    # CORRIGIDO: usa 'name' em vez de 'nome'
    response = supabase.table('usuarios').select('id, name').order('name').execute()
    return response.data

def get_change_logs():
    # CORRIGIDO: usa 'name' em vez de 'nome'
    response = supabase.table('trocas_cartucho').select('*, usuarios(name)').order('data_troca', desc=True).execute()
    return response.data

# --- APLICAÇÃO PRINCIPAL (SÓ RODA SE A SENHA ESTIVER CORRETA) ---
def run_app():
    st.title("🖨️ Gerenciador de Troca de Cartuchos")
    st.markdown("---")

    st.sidebar.title("Menu")
    page = st.sidebar.radio("Selecione uma página", ["Registrar Troca", "Dashboard de Análise", "Gerenciar Setores"])

    # --- PÁGINA: REGISTRAR TROCA ---
    if page == "Registrar Troca":
        st.header("Registrar uma Nova Troca de Cartucho")
        users = get_users()
        # CORRIGIDO: usa 'name' em vez de 'nome'
        user_names = {user['name']: user['id'] for user in users}

        if not users:
            st.warning("Nenhum setor cadastrado. Por favor, adicione um novo setor na página 'Gerenciar Setores' primeiro.")
        else:
            with st.form("registro_troca_form"):
                selected_user_name = st.selectbox("Selecione o Setor:", options=user_names.keys())
                change_date = st.date_input("Data da Troca:", datetime.now())
                
                if st.form_submit_button("Registrar Troca"):
                    user_id = user_names[selected_user_name]
                    formatted_date = change_date.strftime("%Y-%m-%d")
                    try:
                        supabase.table('trocas_cartucho').insert({'usuario_id': user_id, 'data_troca': formatted_date}).execute()
                        st.success(f"Troca registrada com sucesso para {selected_user_name} em {change_date.strftime('%d/%m/%Y')}!")
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao registrar a troca: {e}")

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
                    # CORRIGIDO: usa 'name' e uma forma mais segura para evitar erros
                    'Setor': log.get('usuarios', {}).get('name', 'Setor Desconhecido')
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
                    # CORRIGIDO: usa 'Setor'
                    user_counts = df_filtrado['Setor'].value_counts().reset_index()
                    user_counts.columns = ['Setor', 'Total de Trocas']
                    titulo_grafico_bar = f"Quem mais trocou em {mes_selecionado}" if mes_selecionado != "Todos" else "Quem mais troca cartuchos (Geral)"
                    fig_bar = px.bar(user_counts, x='Setor', y='Total de Trocas', title=titulo_grafico_bar, labels={'Setor': 'Nome do Setor', 'Total de Trocas': 'Quantidade'}, text='Total de Trocas')
                    fig_bar.update_traces(textposition='outside')
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.warning("Nenhum registro encontrado para o período selecionado.")

            with col2:
                st.subheader("Trocas ao Longo do Tempo")
                df['Mês'] = df['Data'].dt.to_period('M').astype(str)
                monthly_changes = df.groupby('Mês').size().reset_index(name='Quantidade')
                fig_line = px.line(monthly_changes.sort_values(by='Mês'), x='Mês', y='Quantidade', title="Volume de Trocas por Mês", markers=True, labels={'Mês': 'Mês/Ano', 'Quantidade': 'Nº de Trocas'})
                st.plotly_chart(fig_line, use_container_width=True)

            st.markdown("---")
            titulo_historico = f"Histórico de Trocas para {mes_selecionado}" if mes_selecionado != "Todos" else "Histórico Completo de Trocas"
            st.subheader(titulo_historico)
            st.dataframe(df_filtrado[['Data', 'Setor']].reset_index(drop=True), use_container_width=True)

    # --- PÁGINA: GERENCIAR SETORES ---
    elif page == "Gerenciar Setores":
        st.header("Gerenciar Setores")
        with st.form("novo_usuario_form"):
            new_user_name = st.text_input("Nome do Novo Setor:")
            if st.form_submit_button("Adicionar Setor"):
                if new_user_name:
                    try:
                        existing_users = get_users()
                        # CORRIGIDO: usa 'name'
                        if any(user['name'].lower() == new_user_name.lower() for user in existing_users):
                            st.warning(f"Setor '{new_user_name}' já existe!")
                        else:
                            # CORRIGIDO: usa 'name'
                            supabase.table('usuarios').insert({'name': new_user_name}).execute()
                            st.success(f"Setor '{new_user_name}' adicionado com sucesso!")
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao adicionar o setor: {e}")

        st.markdown("---")
        st.subheader("Lista de Setores Cadastrados")
        users_data = get_users()
        if users_data:
            # CORRIGIDO: usa 'name'
            df_users = pd.DataFrame(users_data)[['name']].rename(columns={'name': 'Nome do Setor'})
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("Nenhum setor cadastrado.")

# --- LÓGICA PRINCIPAL DE EXECUÇÃO ---
# Primeiro, verifica a senha. Se estiver correta, executa a aplicação.
if check_password():
    run_app()