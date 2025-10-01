import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
# Alteração 1: Importar a biblioteca do MySQL/MariaDB ao invés do psycopg2
import mysql.connector

# --- CONFIGURAÇÃO DA PÁGINA E CONEXÃO MARIADB ---
st.set_page_config(layout="wide", page_title="Gerenciador de Suprimentos")

@st.cache_resource
def init_connection():
    """Função de conexão reescrita para MariaDB/MySQL."""
    try:
        # Alteração 2: Usar mysql.connector.connect e ler as secrets da seção [mariadb]
        conn = mysql.connector.connect(
            host=st.secrets["connections"]["mariadb"]["host"],
            port=st.secrets["connections"]["mariadb"]["port"],
            database=st.secrets["connections"]["mariadb"]["database"], # 'database' ao invés de 'dbname'
            user=st.secrets["connections"]["mariadb"]["username"], # 'username' ao invés de 'user'
            password=st.secrets["connections"]["mariadb"]["password"],
        )
        return conn
    except mysql.connector.Error as e:
        st.error(f"Erro ao conectar ao MariaDB: {e}")
        st.info("Verifique se o serviço do MariaDB está rodando e se as credenciais em secrets.toml estão corretas.")
        return None

db_conn = init_connection()

# --- FUNÇÕES AUXILIARES PARA INTERAÇÃO COM O BANCO ---

def execute_query(query, params=None, fetch=None):
    """Função central para executar queries de forma segura."""
    if not db_conn: return None
    try:
        # Alteração 3: Usar o cursor com 'dictionary=True' para obter resultados como dicionários
        with db_conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
    except Exception as e:
        st.error(f"Erro na query: {e}")
        return None

def commit_changes():
    """Função para aplicar (commit) as alterações no banco. (Nenhuma alteração necessária)"""
    if db_conn: db_conn.commit()

def rollback_changes():
    """Função para reverter (rollback) as alterações em caso de erro. (Nenhuma alteração necessária)"""
    if db_conn: db_conn.rollback()

# --- FUNÇÕES DA APLICAÇÃO (Adaptadas para MariaDB) ---
# Nenhuma alteração necessária aqui, pois as queries SQL são compatíveis.
# O placeholder '%s' é o mesmo para mysql-connector e psycopg2, o que facilita a migração.

def get_users():
    return execute_query("SELECT id, name FROM usuarios ORDER BY name;", fetch="all")

def get_change_logs():
    query = """
        SELECT 
            t.id, t.data_troca, t.observacao,
            u.name as usuarios_name,
            e.modelo as equipamentos_modelo,
            s.modelo as suprimentos_modelo,
            s.categoria as suprimentos_categoria,
            s.tipo as suprimentos_tipo
        FROM trocas_cartucho t
        LEFT JOIN usuarios u ON t.usuario_id = u.id
        LEFT JOIN equipamentos e ON t.equipamento_id = e.id
        LEFT JOIN suprimentos s ON t.suprimento_id = s.id
        ORDER BY t.data_troca DESC;
    """
    logs = execute_query(query, fetch="all")
    if not logs: return []
    processed_logs = []
    for log in logs:
        processed_logs.append({
            'id': log['id'], 'data_troca': log['data_troca'], 'observacao': log.get('observacao', ''),
            'usuarios': {'name': log.get('usuarios_name', 'Setor Desconhecido')},
            'equipamentos': {'modelo': log.get('equipamentos_modelo', 'Não especificado')},
            'suprimentos': {
                'modelo': log.get('suprimentos_modelo', 'Não especificado'),
                'categoria': log.get('suprimentos_categoria', 'Não definida'),
                'tipo': log.get('suprimentos_tipo', 'Não definido')
            }
        })
    return processed_logs

def get_equipamentos(setor_id=None):
    base_query = 'SELECT e.id, e.modelo, e.categoria, u.name as setor_name FROM equipamentos e LEFT JOIN usuarios u ON e.setor_id = u.id'
    params = None
    if setor_id:
        base_query += " WHERE e.setor_id = %s"
        params = (setor_id,)
    base_query += " ORDER BY e.modelo;"
    
    equipamentos = execute_query(base_query, params, fetch="all")
    if not equipamentos: return []
    return [{'id': eq['id'], 'modelo': eq['modelo'], 'categoria': eq['categoria'], 'usuarios': {'name': eq.get('setor_name', 'N/A')}} for eq in equipamentos]

def get_suprimentos(categoria=None):
    query = "SELECT * FROM suprimentos"
    params = None
    if categoria:
        query += " WHERE categoria = %s"
        params = (categoria,)
    query += " ORDER BY modelo;"
    return execute_query(query, params, fetch="all")

# --- APLICAÇÃO PRINCIPAL ---
def run_app():
    logo_url = "https://www.camaraourinhos.sp.gov.br/img/customizacao/cliente/facebook/imagem_compartilhamento_redes.jpg"
    st.sidebar.image(logo_url, use_container_width=True)

    st.title("🖨️ Gerenciador de Suprimentos de Impressão")
    st.markdown("---")

    page = st.sidebar.radio("Selecione uma página", ["Registrar Troca", "Dashboard de Análise", "Gerenciar Setores", "Gerenciar Equipamentos", "Gerenciar Suprimentos"])

    # --- PÁGINA: REGISTRAR TROCA ---
    if page == "Registrar Troca":
        st.header("Registrar uma Nova Troca de Suprimento")
        users = get_users()
        if not users:
            st.warning("Nenhum setor cadastrado.")
        else:
            user_map = {user['name']: user['id'] for user in users}
            selected_user_name = st.selectbox("1. Selecione o Setor:", options=user_map.keys(), index=None, placeholder="Escolha um setor...")
            if selected_user_name:
                selected_user_id = user_map[selected_user_name]
                equipamentos_no_setor = get_equipamentos(setor_id=selected_user_id)
                if not equipamentos_no_setor:
                    st.warning(f"O setor '{selected_user_name}' não possui equipamentos cadastrados.")
                else:
                    equipamento_map = {eq['modelo']: {'id': eq['id'], 'categoria': eq['categoria']} for eq in equipamentos_no_setor}
                    selected_equipamento_modelo = st.selectbox("2. Selecione o Equipamento:", options=equipamento_map.keys(), index=None, placeholder="Escolha um equipamento...")
                    if selected_equipamento_modelo:
                        selected_equipamento_id = equipamento_map[selected_equipamento_modelo]['id']
                        categoria_do_equipamento = equipamento_map[selected_equipamento_modelo]['categoria']
                        if not categoria_do_equipamento:
                            st.error(f"O equipamento '{selected_equipamento_modelo}' não tem uma categoria definida.")
                        else:
                            suprimentos_disponiveis = get_suprimentos(categoria=categoria_do_equipamento)
                            if not suprimentos_disponiveis:
                                st.warning(f"Nenhum suprimento da categoria '{categoria_do_equipamento}' cadastrado.")
                            else:
                                suprimento_map = {f"{sup['modelo']} ({sup['tipo']})": sup['id'] for sup in suprimentos_disponiveis}
                                st.markdown("---")
                                with st.form("registro_troca_form"):
                                    st.info(f"Registrando para: **{selected_user_name}** | **{selected_equipamento_modelo}**")
                                    suprimento_selecionado_modelo = st.selectbox("3. Selecione o Suprimento Trocado:", options=suprimento_map.keys())
                                    change_date = st.date_input("4. Data da Troca:", datetime.now())
                                    observacao = st.text_area("5. Observações (opcional):")
                                    if st.form_submit_button("Registrar Troca"):
                                        if not suprimento_selecionado_modelo:
                                            st.error("Por favor, selecione um suprimento.")
                                        else:
                                            suprimento_id = suprimento_map[suprimento_selecionado_modelo]
                                            try:
                                                query = "INSERT INTO trocas_cartucho (usuario_id, equipamento_id, data_troca, suprimento_id, observacao) VALUES (%s, %s, %s, %s, %s);"
                                                params = (selected_user_id, selected_equipamento_id, change_date, suprimento_id, observacao)
                                                execute_query(query, params)
                                                commit_changes()
                                                st.success("Registro de troca criado com sucesso!")
                                                # Limpar campos seria uma boa adição aqui, mas st.rerun() já resolve.
                                            except Exception as e:
                                                rollback_changes()
                                                st.error(f"Falha ao registrar: {e}")

# --- PÁGINA: DASHBOARD DE ANÁLISE ---
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
                    'ID Troca': log.get('id'),
                    'Data': log.get('data_troca'),
                    'Setor': log.get('usuarios', {}).get('name', 'Setor Desconhecido'),
                    'Equipamento': log.get('equipamentos', {}).get('modelo', 'Não especificado'),
                    'Suprimento': log.get('suprimentos', {}).get('modelo', 'Não especificado'),
                    'Categoria': log.get('suprimentos', {}).get('categoria', 'Não definida'),
                    'Tipo': log.get('suprimentos', {}).get('tipo', 'Não definido'),
                    'Observação': log.get('observacao', '')
                })

            df = pd.DataFrame(processed_logs)
            df['Data'] = pd.to_datetime(df['Data'])

            st.sidebar.markdown("---")
            st.sidebar.header("Filtros do Dashboard")

            # Filtro de Categoria
            categorias_filtro = ["Todas"] + sorted(df[df['Categoria'] != 'Não definida']['Categoria'].unique().tolist())
            categoria_filtrada = st.sidebar.selectbox("Filtrar por Categoria:", categorias_filtro)

            # Filtro de Setor
            setores_filtro = ["Todos"] + sorted(df['Setor'].unique().tolist())
            setor_filtrado = st.sidebar.selectbox("Filtrar por Setor:", setores_filtro)
            
            # Filtro de Mês/Ano
            df['AnoMês'] = df['Data'].dt.strftime('%Y-%m')
            lista_meses = ["Todos"] + sorted(df['AnoMês'].unique(), reverse=True)
            mes_selecionado = st.sidebar.selectbox("Filtrar por Mês/Ano:", options=lista_meses)

            # Aplicação dos filtros
            df_filtrado = df.copy()
            if categoria_filtrada != "Todas":
                df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_filtrada]
            if setor_filtrado != "Todos":
                df_filtrado = df_filtrado[df_filtrado['Setor'] == setor_filtrado]
            if mes_selecionado != "Todos":
                df_filtrado = df_filtrado[df_filtrado['AnoMês'] == mes_selecionado]

            st.markdown("### Gráficos de Análise")

            if df_filtrado.empty:
                st.warning("Nenhum registro encontrado para os filtros selecionados.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    if setor_filtrado != "Todos":
                        st.subheader("Total de Trocas por Equipamento")
                        counts = df_filtrado['Equipamento'].value_counts().reset_index()
                        counts.columns = ['Equipamento', 'Total de Trocas']
                        x_axis, label_x = 'Equipamento', 'Equipamento'
                    else:
                        st.subheader("Total de Trocas por Setor")
                        counts = df_filtrado['Setor'].value_counts().reset_index()
                        counts.columns = ['Setor', 'Total de Trocas']
                        x_axis, label_x = 'Setor', 'Nome do Setor'
                    
                    titulo_grafico_bar = f"Filtros: ({setor_filtrado}, {categoria_filtrada}, {mes_selecionado})"
                    fig_bar = px.bar(counts, x=x_axis, y='Total de Trocas', title=titulo_grafico_bar, labels={x_axis: label_x, 'Total de Trocas': 'Quantidade'}, text='Total de Trocas')
                    fig_bar.update_traces(textposition='outside')
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                with col2:
                    st.subheader("Proporção por Tipo de Suprimento")
                    type_counts = df_filtrado['Tipo'].value_counts().reset_index()
                    type_counts.columns = ['Tipo', 'Quantidade']
                    titulo_grafico_pie = f"Filtros: ({setor_filtrado}, {categoria_filtrada}, {mes_selecionado})"
                    fig_pie = px.pie(type_counts, names='Tipo', values='Quantidade', title=titulo_grafico_pie, hole=.3)
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                st.subheader("Trocas ao Longo do Tempo")
                monthly_changes = df.groupby('AnoMês').size().reset_index(name='Quantidade')
                if setor_filtrado != "Todos":
                    monthly_changes = df_filtrado.groupby('AnoMês').size().reset_index(name='Quantidade')

                titulo_grafico_linha = f"Volume de Trocas por Mês ({setor_filtrado}, {categoria_filtrada})"
                fig_line = px.line(monthly_changes.sort_values(by='AnoMês'), x='AnoMês', y='Quantidade', title=titulo_grafico_linha, markers=True, labels={'AnoMês': 'Mês/Ano', 'Quantidade': 'Nº de Trocas'})
                st.plotly_chart(fig_line, use_container_width=True)
            
            st.markdown("---")
            col_titulo, col_download = st.columns([3, 1])
            with col_titulo:
                titulo_historico = f"Histórico de Trocas ({setor_filtrado}, {categoria_filtrada}, {mes_selecionado})"
                st.subheader(titulo_historico)

            with col_download:
                @st.cache_data
                def convert_df_to_csv(df_to_convert):
                    return df_to_convert.to_csv(index=False).encode('utf-8')
                
                df_export = df_filtrado[['Data', 'Setor', 'Equipamento', 'Suprimento', 'Categoria', 'Tipo', 'Observação']].copy()
                df_export['Data'] = pd.to_datetime(df_export['Data']).dt.strftime('%d/%m/%Y')
                csv = convert_df_to_csv(df_export)

                st.download_button(
                    label="📥 Exportar para CSV",
                    data=csv,
                    file_name=f'historico_trocas_{setor_filtrado}_{categoria_filtrada}_{mes_selecionado}.csv',
                    mime='text/csv',
                )

            if st.session_state.deleting_log_id is not None:
                log_details = df[df['ID Troca'] == st.session_state.deleting_log_id].iloc[0]
                st.warning(f"Você tem certeza que deseja apagar o registro abaixo?")
                st.write(f"**Data:** {log_details['Data'].strftime('%d/%m/%Y')}, **Setor:** {log_details['Setor']}, **Equipamento:** {log_details['Equipamento']}, **Suprimento:** {log_details['Suprimento']}")
                with st.form("confirm_delete_log_form"):
                    password = st.text_input("Para confirmar, digite a senha de exclusão:", type="password")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.form_submit_button("Sim, apagar registro", type="primary"):
                            delete_password = st.secrets.get("auth", {}).get("delete_password", st.secrets.get("auth", {}).get("password", "default_pass"))
                            if password == delete_password:
                                try:
                                    execute_query("DELETE FROM trocas_cartucho WHERE id = %s;", (st.session_state.deleting_log_id,))
                                    commit_changes()
                                    st.success("Registro apagado com sucesso!")
                                    st.session_state.deleting_log_id = None
                                    st.rerun()
                                except Exception as e:
                                    rollback_changes()
                                    st.error(f"Ocorreu um erro ao apagar o registro: {e}")
                            else:
                                st.error("Senha de exclusão incorreta.")
                    with col_cancel:
                        if st.form_submit_button("Cancelar"):
                            st.session_state.deleting_log_id = None
                            st.rerun()

            def set_sort_order(column_name):
                if st.session_state.sort_by == column_name:
                    st.session_state.sort_ascending = not st.session_state.sort_ascending
                else:
                    st.session_state.sort_by = column_name
                    st.session_state.sort_ascending = True
                st.session_state.deleting_log_id = None

            df_sorted = df_filtrado.sort_values(by=st.session_state.sort_by, ascending=st.session_state.sort_ascending)
            
            # Cabeçalhos da tabela
            header_cols = st.columns([2, 3, 3, 3, 2, 2, 1, 1])
            if header_cols[0].button('Data'): set_sort_order('Data')
            if header_cols[1].button('Setor'): set_sort_order('Setor')
            if header_cols[2].button('Equipamento'): set_sort_order('Equipamento')
            if header_cols[3].button('Suprimento'): set_sort_order('Suprimento')
            if header_cols[4].button('Categoria'): set_sort_order('Categoria')
            if header_cols[5].button('Tipo'): set_sort_order('Tipo')
            header_cols[6].write("**OBS**")
            header_cols[7].write("**Ação**")
            st.markdown("<hr style='margin-top: -0.5em; margin-bottom: 0.5em;'>", unsafe_allow_html=True)

            # Loop para exibir cada linha de dados
            for index, row in df_sorted.iterrows():
                row_cols = st.columns([2, 3, 3, 3, 2, 2, 1, 1])
                
                row_cols[0].text(row['Data'].strftime('%d/%m/%Y'))
                row_cols[1].text(row['Setor'])
                row_cols[2].text(row['Equipamento'])
                row_cols[3].text(row['Suprimento'])
                row_cols[4].text(row['Categoria'])
                row_cols[5].text(row['Tipo'])

                obs_text = row['Observação']
                if pd.notna(obs_text) and obs_text.strip():
                    with row_cols[6].popover("👁️", help="Ver observação"):
                        st.info(obs_text)
                else:
                    row_cols[6].write("")

                if row_cols[7].button("🗑️", key=f"del_log_{row['ID Troca']}", help="Remover este registro"):
                    st.session_state.deleting_log_id = row['ID Troca']
                    st.rerun()

    # --- PÁGINA: GERENCIAR SETORES ---
    elif page == "Gerenciar Setores":
        st.header("Gerenciar Setores")
        if 'editing_sector_id' not in st.session_state: st.session_state.editing_sector_id = None
        if 'deleting_sector_id' not in st.session_state: st.session_state.deleting_sector_id, st.session_state.deleting_sector_name, st.session_state.deleting_sector_logs_count = None, None, 0

        if st.session_state.deleting_sector_id is not None:
            st.warning(f"⚠️ **ATENÇÃO:** Você está prestes a apagar o setor **'{st.session_state.deleting_sector_name}'** e todos os seus **{st.session_state.deleting_sector_logs_count}** registros. Esta ação é irreversível.")
            with st.form("confirm_delete_form"):
                password = st.text_input("Para confirmar, digite a senha de exclusão:", type="password")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.form_submit_button("Confirmar Exclusão Permanente", type="primary"):
                        delete_password = st.secrets.get("auth", {}).get("delete_password", st.secrets.get("auth", {}).get("password", "default_pass"))
                        if password == delete_password:
                            try:
                                # A exclusão em cascata (ON DELETE CASCADE) no SQL cuidaria disso, 
                                # mas para garantir, podemos deletar os logs primeiro.
                                execute_query("DELETE FROM trocas_cartucho WHERE usuario_id = %s;", (st.session_state.deleting_sector_id,))
                                execute_query("DELETE FROM usuarios WHERE id = %s;", (st.session_state.deleting_sector_id,))
                                commit_changes()
                                st.success(f"O setor '{st.session_state.deleting_sector_name}' e seus registros foram removidos!")
                                st.session_state.deleting_sector_id = None
                                st.rerun()
                            except Exception as e:
                                rollback_changes()
                                st.error(f"Ocorreu um erro durante a exclusão: {e}")
                        else:
                            st.error("Senha de exclusão incorreta.")
                with col_cancel:
                    if st.form_submit_button("Cancelar"):
                        st.session_state.deleting_sector_id = None
                        st.rerun()
        else:
            with st.expander("Adicionar Novo Setor", expanded=(st.session_state.editing_sector_id is None)):
                with st.form("novo_setor_form", clear_on_submit=True):
                    new_user_name = st.text_input("Nome do Novo Setor:")
                    if st.form_submit_button("Adicionar Setor"):
                        if new_user_name:
                            try:
                                execute_query("INSERT INTO usuarios (name) VALUES (%s);", (new_user_name,))
                                commit_changes()
                                st.success(f"Setor '{new_user_name}' adicionado!")
                                st.rerun()
                            except Exception as e:
                                rollback_changes()
                                st.error(f"Ocorreu um erro: {e}")
            st.markdown("---")
            st.subheader("Lista de Setores Cadastrados")
            users_data = get_users()
            if not users_data:
                st.info("Nenhum setor cadastrado.")
            else:
                for user in users_data:
                    user_id, user_name = user['id'], user['name']
                    with st.container(border=True):
                        if st.session_state.editing_sector_id == user_id:
                            # Lógica de edição
                            new_name = st.text_input("Novo nome:", value=user_name, key=f"edit_input_{user_id}")
                            if st.button("✔️ Salvar", key=f"save_{user_id}"):
                                if new_name and new_name != user_name:
                                    try:
                                        execute_query("UPDATE usuarios SET name = %s WHERE id = %s;", (new_name, user_id))
                                        commit_changes()
                                        st.success(f"Setor renomeado para '{new_name}'!")
                                        st.session_state.editing_sector_id = None
                                        st.rerun()
                                    except Exception as e:
                                        rollback_changes()
                                        st.error(f"Erro ao atualizar: {e}")
                                else:
                                    st.session_state.editing_sector_id = None
                                    st.rerun()
                        else:
                            # Lógica de exibição
                            col1, col2, col3 = st.columns([0.8, 0.1, 0.1])
                            col1.markdown(f"<p style='margin-top: 5px; font-size: 1.1em;'>{user_name}</p>", unsafe_allow_html=True)
                            if col2.button("✏️", key=f"edit_{user_id}"):
                                st.session_state.editing_sector_id = user_id
                                st.rerun()
                            if col3.button("🗑️", key=f"delete_{user_id}"):
                                count_result = execute_query("SELECT count(*) as total FROM trocas_cartucho WHERE usuario_id = %s;", (user_id,), fetch="one")
                                log_count = count_result['total'] if count_result else 0
                                if log_count > 0:
                                    st.session_state.deleting_sector_id, st.session_state.deleting_sector_name, st.session_state.deleting_sector_logs_count = user_id, user_name, log_count
                                    st.rerun()
                                else:
                                    try:
                                        execute_query("DELETE FROM usuarios WHERE id = %s;", (user_id,))
                                        commit_changes()
                                        st.success(f"Setor '{user_name}' removido com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        rollback_changes()
                                        st.error(f"Ocorreu um erro ao remover '{user_name}': {e}")
    
    # --- PÁGINA: GERENCIAR EQUIPAMENTOS ---
    elif page == "Gerenciar Equipamentos":
        st.header("Gerenciar Equipamentos")
        with st.expander("Adicionar Novo Equipamento"):
            users_data = get_users()
            if not users_data:
                st.warning("Cadastre um setor antes de adicionar um equipamento.")
            else:
                setor_map = {user['name']: user['id'] for user in users_data}
                with st.form("novo_equipamento_form", clear_on_submit=True):
                    modelo = st.text_input("Modelo do Equipamento:")
                    categoria = st.selectbox("Categoria do Suprimento:", ["Cartucho de Tinta", "Suprimento Laser"])
                    setor_nome = st.selectbox("Associar ao Setor:", options=setor_map.keys())
                    if st.form_submit_button("Adicionar Equipamento"):
                        if modelo and setor_nome and categoria:
                            setor_id = setor_map[setor_nome]
                            try:
                                query = "INSERT INTO equipamentos (modelo, setor_id, categoria) VALUES (%s, %s, %s);"
                                execute_query(query, (modelo, setor_id, categoria))
                                commit_changes()
                                st.success(f"Equipamento '{modelo}' adicionado!")
                                st.rerun()
                            except Exception as e:
                                rollback_changes()
                                st.error(f"Erro ao adicionar equipamento: {e}")
                        else:
                            st.error("Preencha todos os campos.")
        st.markdown("---")
        st.subheader("Lista de Equipamentos Cadastrados")
        equipamentos_data = get_equipamentos()
        if not equipamentos_data:
            st.info("Nenhum equipamento cadastrado.")
        else:
            for item in equipamentos_data:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    col1.text(item['modelo'])
                    col2.text(item.get('categoria', 'N/A'))
                    col3.text(item['usuarios']['name'])
                    if col4.button("🗑️", key=f"del_equip_{item['id']}"):
                        # Lógica de deleção (com aviso)
                        st.error("A deleção de equipamentos ainda precisa ser implementada com a confirmação de senha.")

    # --- PÁGINA: GERENCIAR SUPRIMENTOS ---
    elif page == "Gerenciar Suprimentos":
        st.header("Gerenciar Suprimentos (Catálogo)")
        with st.expander("Adicionar Novo Suprimento ao Catálogo"):
            with st.form("novo_suprimento_form", clear_on_submit=True):
                modelo = st.text_input("Modelo (ex: HP 664)")
                categoria = st.selectbox("Categoria", ["Cartucho de Tinta", "Suprimento Laser"])
                tipo = None
                if categoria == "Cartucho de Tinta":
                    tipo = st.selectbox("Tipo", ["Preto", "Colorido"])
                elif categoria == "Suprimento Laser":
                    tipo = st.selectbox("Tipo", ["Toner", "Cilindro"])
                if st.form_submit_button("Adicionar Suprimento"):
                    if modelo and categoria and tipo:
                        try:
                            query = "INSERT INTO suprimentos (modelo, categoria, tipo) VALUES (%s, %s, %s);"
                            execute_query(query, (modelo, categoria, tipo))
                            commit_changes()
                            st.success(f"Suprimento '{modelo}' adicionado!")
                            st.rerun()
                        except Exception as e:
                            rollback_changes()
                            st.error(f"Erro ao adicionar suprimento: {e}")
                    else:
                        st.error("Preencha todos os campos.")
        st.markdown("---")
        st.subheader("Catálogo de Suprimentos Cadastrados")
        suprimentos_data = get_suprimentos()
        if not suprimentos_data:
            st.info("Nenhum suprimento cadastrado.")
        else:
            for item in suprimentos_data:
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    col1.text(item['modelo'])
                    col2.text(item.get('categoria', 'N/A'))
                    col3.text(item.get('tipo', 'N/A'))
                    if col4.button("🗑️", key=f"del_sup_{item['id']}"):
                        # Lógica de deleção (com aviso)
                         st.error("A deleção de suprimentos ainda precisa ser implementada com a confirmação de senha.")

# --- LÓGICA PRINCIPAL DE EXECUÇÃO ---
if __name__ == "__main__":
    if db_conn:
        run_app()
    else:
        st.header("🔴 Erro de Conexão com o Banco de Dados")
        st.warning("A aplicação não pode ser iniciada.")
