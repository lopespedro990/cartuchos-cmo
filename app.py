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
    response = supabase.table('trocas_cartucho').select('*, usuarios(name)').order('data_troca', desc=True).execute()
    return response.data

# --- APLICAÇÃO PRINCIPAL ---
def run_app():
    logo_url = "https://www.camaraou.sp.gov.br/imagens/logo-horizontal-branco-e-verde-2.png/image"
    st.sidebar.image(logo_url, use_container_width=True)

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
                
                st.markdown("**Marque o(s) tipo(s) de cartucho trocado(s):**")
                col_preto, col_colorido = st.columns(2)
                trocou_preto = col_preto.checkbox("Preto")
                trocou_colorido = col_colorido.checkbox("Colorido")
                
                change_date = st.date_input("Data da Troca:", datetime.now())
                
                if st.form_submit_button("Registrar Troca"):
                    
                    tipos_a_registrar = []
                    if trocou_preto:
                        tipos_a_registrar.append("Preto")
                    if trocou_colorido:
                        tipos_a_registrar.append("Colorido")
                    
                    if not tipos_a_registrar:
                        st.error("Por favor, selecione pelo menos um tipo de cartucho.")
                    else:
                        user_id = user_names[selected_user_name]
                        formatted_date = change_date.strftime("%Y-%m-%d")
                        
                        erros = []
                        sucessos = 0
                        
                        for tipo in tipos_a_registrar:
                            try:
                                supabase.table('trocas_cartucho').insert({
                                    'usuario_id': user_id, 
                                    'data_troca': formatted_date,
                                    'tipo_cartucho': tipo
                                }).execute()
                                sucessos += 1
                            except Exception as e:
                                erros.append(f"Falha ao registrar cartucho '{tipo}': {e}")

                        if sucessos > 0:
                            st.success(f"{sucessos} registro(s) de troca criado(s) com sucesso para {selected_user_name}!")
                        if erros:
                            for erro in erros:
                                st.error(erro)

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

            with col2:
                st.subheader("Proporção por Tipo de Cartucho")
                if not df_filtrado.empty:
                    type_counts = df_filtrado['Tipo'].value_counts().reset_index()
                    type_counts.columns = ['Tipo', 'Quantidade']
                    titulo_grafico_pie = f"Proporção em {mes_selecionado}" if mes_selecionado != "Todos" else "Proporção Geral"
                    fig_pie = px.pie(type_counts, names='Tipo', values='Quantidade', title=titulo_grafico_pie, hole=.3)
                    st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("Trocas ao Longo do Tempo")
            monthly_changes = df.groupby('AnoMês').size().reset_index(name='Quantidade')
            fig_line = px.line(monthly_changes.sort_values(by='AnoMês'), x='AnoMês', y='Quantidade', title="Volume de Trocas por Mês", markers=True, labels={'AnoMês': 'Mês/Ano', 'Quantidade': 'Nº de Trocas'})
            st.plotly_chart(fig_line, use_container_width=True)
            
            st.markdown("---")
            titulo_historico = f"Histórico de Trocas para {mes_selecionado}" if mes_selecionado != "Todos" else "Histórico Completo de Trocas"
            st.subheader(titulo_historico)
            st.dataframe(df_filtrado[['Data', 'Setor', 'Tipo']].reset_index(drop=True), use_container_width=True)

    # --- PÁGINA: GERENCIAR SETORES (REESTRUTURADA) ---
    elif page == "Gerenciar Setores":
        st.header("Gerenciar Setores")

        # Seção para adicionar novo setor
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
        
        # Seção para listar e remover setores existentes
        st.subheader("Lista de Setores Cadastrados")
        users_data = get_users()
        
        if not users_data:
            st.info("Nenhum setor cadastrado.")
        else:
            # Loop para exibir cada setor com seu botão de remover
            for user in users_data:
                user_id = user['id']
                user_name = user['name']
                
                col1, col2 = st.columns([4, 1]) # Coluna do nome maior que a do botão
                
                with col1:
                    st.text(user_name)
                
                with col2:
                    # Cria um botão único para cada setor usando a 'key'
                    if st.button("Remover", key=f"delete_{user_id}", type="primary"):
                        # Passo 1: Verificar se o setor tem registros de troca associados
                        response = supabase.table('trocas_cartucho').select('id', count='exact').eq('usuario_id', user_id).execute()
                        
                        if response.count > 0:
                            st.error(f"'{user_name}' não pode ser removido pois possui {response.count} registro(s) associados.")
                        else:
                            # Passo 2: Se não houver registros, permitir a remoção
                            try:
                                supabase.table('usuarios').delete().eq('id', user_id).execute()
                                st.success(f"Setor '{user_name}' removido com sucesso!")
                                st.rerun() # Recarrega a página para atualizar a lista
                            except Exception as e:
                                st.error(f"Ocorreu um erro ao remover '{user_name}': {e}")
                st.markdown("---") # Linha divisória para cada item

# --- LÓGICA PRINCIPAL DE EXECUÇÃO ---
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False

if st.session_state['password_correct']:
    run_app()
else:
    show_login_form()