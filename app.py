import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA E SUPABASE ---

# Configura o layout da página para ser mais largo
st.set_page_config(layout="wide", page_title="Gerenciador de Troca de Cartuchos")

# Inicializa a conexão com o Supabase usando as credenciais do secrets.toml
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNÇÕES AUXILIARES ---

# Função para buscar todos os usuários
def get_users():
    response = supabase.table('usuarios').select('id, nome').order('nome').execute()
    return response.data

# Função para buscar todos os registros de troca com o nome do usuário
def get_change_logs():
    # Este select é poderoso: ele pega tudo de 'trocas_cartucho' E o campo 'nome' da tabela 'usuarios' relacionada
    response = supabase.table('trocas_cartucho').select('*, usuarios(nome)').order('data_troca', desc=True).execute()
    return response.data

# --- INTERFACE DA APLICAÇÃO ---

st.title("🖨️ Gerenciador de Troca de Cartuchos")
st.markdown("---")

# --- BARRA LATERAL PARA NAVEGAÇÃO ---
st.sidebar.title("Menu")
page = st.sidebar.radio("Selecione uma página", ["Registrar Troca", "Dashboard de Análise", "Gerenciar Usuários"])

# --- PÁGINA: REGISTRAR TROCA ---
if page == "Registrar Troca":
    st.header("Registrar uma Nova Troca de Cartucho")

    # Busca os usuários para popular o selectbox
    users = get_users()
    user_names = {user['nome']: user['id'] for user in users} # Dicionário para mapear nome -> id

    if not users:
        st.warning("Nenhum setor cadastrado. Por favor, adicione um novo setor na página 'Gerenciar Usuários' primeiro.")
    else:
        with st.form("registro_troca_form"):
            selected_user_name = st.selectbox("Selecione o Setor:", options=user_names.keys())
            change_date = st.date_input("Data da Troca:", datetime.now())
            
            submitted = st.form_submit_button("Registrar Troca")

            if submitted:
                # Pega o ID do usuário selecionado
                user_id = user_names[selected_user_name]
                
                # Formata a data para o formato YYYY-MM-DD
                formatted_date = change_date.strftime("%Y-%m-%d")

                # Insere os dados na tabela 'trocas_cartucho'
                try:
                    supabase.table('trocas_cartucho').insert({
                        'usuario_id': user_id,
                        'data_troca': formatted_date
                    }).execute()
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
        # Processa os dados para o DataFrame do Pandas
        processed_logs = []
        for log in logs:
            processed_logs.append({
                'ID Troca': log['id'],
                'Data': log['data_troca'],
                # CORREÇÃO IMPORTANTE: Alterado de 'nome' para 'name'
                'Usuário': log['usuarios']['nome'] if log.get('usuarios') else 'Usuário Desconhecido'
            })
        
        df = pd.DataFrame(processed_logs)
        df['Data'] = pd.to_datetime(df['Data'])
        df = df.sort_values(by='Data', ascending=False)

        # --- IMPLEMENTAÇÃO DO FILTRO DE MÊS ---
        st.sidebar.markdown("---")
        st.sidebar.header("Filtros do Dashboard")

        # Cria uma coluna 'AnoMês' para usar no filtro
        df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
        
        # Cria a lista de opções para o filtro, começando com "Todos"
        lista_meses = sorted(df['AnoMês'].unique(), reverse=True)
        lista_meses.insert(0, "Todos")

        # Cria o widget de seleção na barra lateral
        mes_selecionado = st.sidebar.selectbox(
            "Filtrar Setor por Mês/Ano:",
            options=lista_meses
        )

        # Filtra os dados com base na seleção
        if mes_selecionado == "Todos":
            df_filtrado = df
        else:
            df_filtrado = df[df['AnoMês'] == mes_selecionado]
        
        # --- FIM DA IMPLEMENTAÇÃO DO FILTRO ---

        st.markdown("### Gráficos de Análise")
        
        col1, col2 = st.columns(2)

        with col1:
            # Gráfico 1: Total de trocas por usuário (agora usa df_filtrado)
            st.subheader("Total de Trocas por Setor")

            if not df_filtrado.empty:
                user_counts = df_filtrado['Usuário'].value_counts().reset_index()
                user_counts.columns = ['Usuário', 'Total de Trocas']
                
                # Título dinâmico para o gráfico
                titulo_grafico_bar = f"Quem mais trocou em {mes_selecionado}" if mes_selecionado != "Todos" else "Quem mais troca cartuchos (Geral)"
                
                fig_bar = px.bar(user_counts, x='Usuário', y='Total de Trocas', 
                                 title=titulo_grafico_bar,
                                 labels={'Usuário': 'Nome do Usuário', 'Total de Trocas': 'Quantidade'},
                                 text='Total de Trocas')
                fig_bar.update_traces(textposition='outside')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.warning("Nenhum registro encontrado para o período selecionado.")

        with col2:
            # Gráfico 2: Trocas ao longo do tempo (usa o df original para mostrar a tendência geral)
            st.subheader("Trocas ao Longo do Tempo")
            df['Mês'] = df['Data'].dt.to_period('M').astype(str)
            monthly_changes = df.groupby('Mês').size().reset_index(name='Quantidade')
            
            fig_line = px.line(monthly_changes.sort_values(by='Mês'), x='Mês', y='Quantidade', 
                               title="Volume de Trocas por Mês",
                               markers=True,
                               labels={'Mês': 'Mês/Ano', 'Quantidade': 'Nº de Trocas'})
            st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")
        
        # Título dinâmico para a tabela de histórico
        titulo_historico = f"Histórico de Trocas para {mes_selecionado}" if mes_selecionado != "Todos" else "Histórico Completo de Trocas"
        st.subheader(titulo_historico)

        # Exibe o DataFrame filtrado
        st.dataframe(
            df_filtrado[['Data', 'Usuário']].reset_index(drop=True), 
            use_container_width=True
        )


# --- PÁGINA: GERENCIAR USUÁRIOS ---
elif page == "Gerenciar Usuários":
    st.header("Gerenciar Usuários")

    with st.form("novo_usuario_form"):
        new_user_name = st.text_input("Nome do Novo Usuário:")
        submitted = st.form_submit_button("Adicionar Usuário")

        if submitted and new_user_name:
            try:
                # Verifica se o usuário já existe
                existing_users = get_users()
                if any(user['nome'].lower() == new_user_name.lower() for user in existing_users):
                    st.warning(f"Usuário '{new_user_name}' já existe!")
                else:
                    supabase.table('usuarios').insert({'nome': new_user_name}).execute()
                    st.success(f"Usuário '{new_user_name}' adicionado com sucesso!")
            except Exception as e:
                st.error(f"Ocorreu um erro ao adicionar o usuário: {e}")

    st.markdown("---")
    st.subheader("Lista de Usuários Cadastrados")
    
    users_data = get_users()
    if users_data:
        df_users = pd.DataFrame(users_data)[['nome']]
        df_users.rename(columns={'nome': 'Nome do Usuário'}, inplace=True)
        st.dataframe(df_users, use_container_width=True)
    else:
        st.info("Nenhum usuário cadastrado.")