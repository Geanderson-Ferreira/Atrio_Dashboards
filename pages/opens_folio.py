import streamlit as st
import pandas as pd
from os import environ
from dotenv import load_dotenv
from os import environ
import plotly.express as px
import pyodbc

# load_dotenv()

server = environ.get('SERVER')
database = environ.get('DATABASE')
username = environ.get('DB_USER')
password = environ.get('DB_PASSWORD')

st.write(server)


conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Trusted_Connection=yes;'
conn = pyodbc.connect(conn_str)

#Obtem os resultados das ultimas 30 coletas de informações
query_inicial = """
SELECT * 
FROM dbo.openfolios 
WHERE snap_date BETWEEN DATEADD(DAY, -30, (SELECT MAX(snap_date) FROM openfolios)) AND (SELECT MAX(snap_date) FROM openfolios);
"""

query_evolution_hoteis = """
SELECT
    hotel_name,
    snap_date,
    SUM(total_balance) AS total_balance
FROM
    openfolios
GROUP BY
    hotel_name,
    snap_date
ORDER BY
    snap_date;
"""

query_evolution_atrio = """
SELECT 
    snap_date, SUM(total_balance) AS total_balance
FROM
    openfolios
GROUP BY snap_date
ORDER BY snap_date;
"""

# ----------------- DF INICIAL
df_complete = pd.read_sql(query_inicial, conn)


cols_to_date = ['arrival_date', 'departure_date', 'snap_date', 'reservation_date']
date_default = "%d/%m/%Y"

for col in cols_to_date:
    df_complete[col] = pd.to_datetime(df_complete[col])#.dt.strftime(date_default)


df = df_complete[df_complete['snap_date'] == df_complete['snap_date'].max()]

#------------------- Funções de formatação

def to_money(value):
    # Formate o valor como uma string monetária com vírgula como separador de milhares e ponto como separador decimal
    return "{:,.2f}".format(value).replace(',', 'X').replace('.', ',').replace('X', '.')


#----------------- SIDEBAR
st.set_page_config(layout="wide")#,initial_sidebar_state="collapsed")
st.sidebar.markdown("Criado por TI Atrio")
st.sidebar.title("Filtros - Opens Folio")
hotel = st.sidebar.selectbox("Hotel", ["Atrio"] + sorted(df['hotel_name'].unique()))
checkout = st.sidebar.date_input("Checkout até",format="DD/MM/YYYY")
estornos = st.sidebar.checkbox("Filtrar por Positivos", value=False, key=None, help=None, on_change=None, disabled=False, label_visibility="visible")


#-------------------  APLICANDO FILTROS NO DF
df_filtered = df

if hotel != "Atrio":
    df_filtered = df[df['hotel_name'] == hotel]

df_filtered = df_filtered[df_filtered['departure_date'] < pd.to_datetime(checkout)]

if estornos:
    df_filtered = df_filtered[df['total_balance'] > 0]

#----------------------- TITULO
st.title("Contas em Aberto - " +  hotel)

#---------------------- PRIMEIRO DATAFRAME
df_to_show = df_filtered[['reservation_conf', 'hotel_id', 'total_balance', 'guest_first_name', 'guest_surname', 'routing', 'arrival_date', 'departure_date', 'reservation_date', 'room_number']]
for col in ['arrival_date', 'departure_date', 'reservation_date']:

    df_to_show[col] = pd.to_datetime(df_to_show[col]).dt.strftime(date_default)

df_to_show = df_to_show.sort_values(by=['total_balance'],ascending=False)
df_to_show['total_balance'] = df_to_show['total_balance'].apply(to_money)


st.dataframe(df_to_show, hide_index=True)


#----------------------- ROTULO ABAIXO
st.warning(f"Total filtrado: {to_money(df_filtered['total_balance'].sum())}")


#----------------------- CALCULA RESUMO
if hotel != "Atrio" :
    df_results = df[df['hotel_name'] == hotel]
else:
    df_results = df

total_contas_abertas = df_results['total_balance'].count()
total_valor_contas_abertas = df_results['total_balance'].sum()
total_contas_positivas = df_results[df_results['total_balance'] > 0]['total_balance'].count()
total_valor_contas_positivas = df_results[df_results['total_balance'] > 0]['total_balance'].sum()
total_contas_negativas = df_results[df_results['total_balance'] < 0]['total_balance'].count()
total_valor_contas_negativas = df_results[df_results['total_balance'] < 0]['total_balance'].sum()

#---------------------- MOSTRA RESUMO
st.title("Resumo")
with st.container(height=150):
    st.write(f"{'{:,}'.format(total_contas_abertas).replace(',','.')} contas abertas: {to_money(total_valor_contas_abertas)}")
    st.write(f"{'{:,}'.format(total_contas_positivas).replace(',','.')} contas positivas: {to_money(total_valor_contas_positivas)}")
    st.write(f"{'{:,}'.format(total_contas_negativas).replace(',','.')} contas negativas: {to_money(total_valor_contas_negativas)}")

#--------------------- MOSTRA EVOLUÇÃO
st.title("Evolução últimos 30 dias")
if hotel != 'Atrio':
    df_evolution = df_complete.groupby(["hotel_name", "snap_date"])['total_balance'].sum().reset_index().sort_values(by=['snap_date'])
    fig = px.line(df_evolution[df_evolution['hotel_name'] == hotel], x="snap_date", y="total_balance", text=df_evolution[df_evolution['hotel_name'] == hotel]['total_balance'].apply(to_money))
    st.plotly_chart(fig, use_container_width=True)

else:
    df_evolution = df_complete.groupby("snap_date")['total_balance'].sum().reset_index().sort_values(by=['snap_date'])
    fig = px.line(df_evolution, x="snap_date", y="total_balance", text=df_evolution['total_balance'].apply(to_money))
    st.plotly_chart(fig, use_container_width=True)

#--------------------- AGRUPA
total_por_hotel = df.groupby("hotel_name")["total_balance"].sum().reset_index().sort_values(by=['total_balance'],ascending=True)

#--------------------- GRAFICO AGRUPADO 10 MAIS
fig_date = px.bar(total_por_hotel.tail(10), x="total_balance", y="hotel_name" ,title="10 maiores",text=total_por_hotel.tail(10)['total_balance'].apply(to_money))
fig_date.update_yaxes(visible=True)
st.plotly_chart(fig_date, use_container_width=True)

#--------------------- DATAFRAME AGRUPADO
st.write("Total Hoteis")
total_por_hotel = total_por_hotel.sort_values(by=['total_balance'], ascending=False)
total_por_hotel['total_balance'] = total_por_hotel['total_balance'].apply(to_money)
st.dataframe(total_por_hotel, use_container_width=True, hide_index=True)