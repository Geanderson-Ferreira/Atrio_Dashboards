import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import plotly.express as px
from os import environ

load_dotenv()

import pyodbc

server = environ.get('SERVER')
database = environ.get('DATABASE')
username = environ.get('DB_USER')
password = environ.get('DB_PASSWORD')


conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
conn = pyodbc.connect(conn_str)


table_name = "dbo.Transactions"

col_hotel_name = "hotelID"
col_postingDate = "transactionDate"
col_transactionCode = "transactionDescription"
col_transactionType = "transactionType"
col_amount = "transactionAmount"
col_reference = "transactionReference"
col_cashierInfo = "cashier_name"
col_quantity = "transactionQuantity"
col_transactionNo = "transactionID"
col_resvId = "resvNameID"
col_transactionHour = "detailImported"
col_user_name = "cashier_name" #--------------------Ajustar à coluna com nome de usuario
select_all = "Todos"

#---------config da pagina
st.set_page_config(layout="wide")

#------------------ Criação da Sidebar / Hotel e Mês serão filtros para a query inicial / criação do primeiro DF
if 'hoteis' not in st.session_state:
    df_nome_hoteis = pd.read_sql(f"SELECT DISTINCT {col_hotel_name} FROM {table_name}", conn)
    st.session_state['hoteis'] = df_nome_hoteis


#------------------- Funções de formatação
def plot_format(valor):
    numero_arredondado = round(valor)
    numero_formatado = "{:,.0f}".format(numero_arredondado).replace(',', '.')
    return numero_formatado

def to_money(value):
    # Formate o valor como uma string monetária com vírgula como separador de milhares e ponto como separador decimal
    return "{:,.2f}".format(value).replace(',', 'X').replace('.', ',').replace('X', '.')


query_meses = """
SELECT DISTINCT mes 
FROM (
    SELECT *, CONCAT(MONTH(transactionDate), '-', YEAR(transactionDate)) AS mes 
    FROM dbo.Transactions
) AS MEStable 
ORDER BY mes;
"""
if 'df_meses' not in st.session_state:
    df_meses = pd.read_sql(query_meses, conn)
    st.session_state['df_meses'] = df_meses

filter_hotel = st.sidebar.selectbox("Selecione o hotel", st.session_state['hoteis'][col_hotel_name].unique())
filter_month = st.sidebar.selectbox("Selecione o mês",st.session_state['df_meses']['mes'].unique())
filter_month = str(filter_month).split('-')[0]

#------------------ Criação do primeiro DF Geral
gen_query = f"""
SELECT t.*, c.name AS cashier_name, tc.transactionDescription
FROM (
    SELECT *, MONTH({col_postingDate}) AS mes
    FROM {table_name}
) AS t
INNER JOIN cashiers AS c ON t.cashierId = c.cashierId
INNER JOIN transactionCodes AS tc ON t.transactionCode = tc.transactionCode
WHERE t.mes = '{filter_month}' AND t.hotelID = '{filter_hotel}';

"""

df = pd.read_sql(gen_query, conn)
#------------------ Filtro de lançamentos / Obter os nomes das transactions
filter_transactionType = st.sidebar.selectbox("Selecione o tipo de transação", [select_all] + sorted(df[col_transactionType].unique()))
if filter_transactionType != select_all:
    df_filtered = df[df[col_transactionType] == filter_transactionType]
else:
    df_filtered = df

#----------------- Checkbox de negativos
filter_negativos = st.sidebar.checkbox("Filtrar por Negativos", value=False, key=None, help=None, on_change=None, disabled=False, label_visibility="visible")
if filter_negativos:
    df_filtered = df_filtered[df[col_amount] < 0]


#----------------- Filtro de TransactionCode
filter_transactionCode = st.sidebar.selectbox("Selecione o código da Transação", [select_all] + sorted(df[col_transactionCode].unique()))
if filter_transactionCode != select_all:
    df_filtered = df_filtered[df_filtered[col_transactionCode] == filter_transactionCode]


#----------------- Selectbox nome de usuários
filter_cashierInfo = st.sidebar.selectbox("Selecione o Usuário", [select_all] + sorted(df[col_user_name].unique()))
if filter_cashierInfo != select_all:
    df_filtered = df_filtered[df_filtered[col_user_name] == filter_cashierInfo]

#---------------- Titulo
st.title("Lançamentos - " +  filter_hotel)

#---------------- Coloca DataFrame na tela
df_filtered['transactionID'] = df_filtered['transactionID'].apply(lambda x: str(x).replace(".",""))
df_filtered['transactionCode'] = df_filtered['transactionCode'].apply(lambda x: str(x).replace(",",""))
df_filtered['roomNumber'] = df_filtered['roomNumber'].apply(lambda x: str(x).replace(",",""))
df_filtered['transactionDate'] = pd.to_datetime(df_filtered['transactionDate']).dt.strftime("%d/%m/%Y")

df_to_show = df_filtered.copy().sort_values(by=['transactionAmount'])

df_to_show['transactionAmount'] = df_to_show['transactionAmount'].apply(to_money)
st.dataframe(df_to_show, hide_index=True)


# --------------- Valores agrupados por código de lançamento
df_grouped_by_day = df_filtered.groupby([col_postingDate, col_cashierInfo])[col_amount].sum().reset_index()
fig_prod = px.bar(df_grouped_by_day, 
                   x=col_postingDate, 
                   y=col_amount, 
                   color=col_cashierInfo,
                   title="Total Estorno por dia",
                   orientation="v")

st.plotly_chart(fig_prod, use_container_width=True)



# col0, col02 = st.columns(2)
# with col0:
#     st.write("teste")

# col1, col2 = st.columns(2)
# col3, col4, col5 = st.columns(3)

# fig_scatter = px.scatter(df_filtered[(df_filtered['amount'] < 0)|(df_filtered['quantity'] < 0)], x='transactionHour', y="amount", title="Estornos por horário")
# col1.plotly_chart(fig_scatter, use_container_width=False)

# fig_date = px.bar(df_filtered, x="postingDate", y="amount", color="cashierInfo", title="Lançamentos por usuário")
# col2.plotly_chart(fig_date, use_container_width=True, width=800)

# fig_prod = px.bar(df_filtered, x="amount", y="transactionCode", 
#                   color="cashierInfo", title="Valor por transaction code",
#                   orientation="h")
# col3.plotly_chart(fig_prod, use_container_width=True)

# total_estornos_por_usuario = df_filtered[(df_filtered['amount'] < 0)|(df_filtered['quantity'] < 0)].groupby("cashierInfo")["amount"].sum().reset_index()

# # # Criar o gráfico de pizza para exibir o faturamento por tipo de pagamento
# fig_kind = px.pie(total_estornos_por_usuario, values="amount", names="cashierInfo",
#                     title="Faturamento por tipo de pagamento")
# col4.plotly_chart(fig_kind, use_container_width=True)

# # # Exibir o gráfico na quarta coluna
# # col4.plotly_chart(fig_kind, use_container_width=True)
