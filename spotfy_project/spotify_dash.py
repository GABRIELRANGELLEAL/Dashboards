import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

df = pd.read_csv("C:/Users/thiag/OneDrive/Documentos/GitHub/Dashboards/spotfy_project/spotify_data.csv")

artista = df['Artist'].unique()

# help(st.selectbox())

artista_opcoes = ['Todos'] + list(artista)

artist = st.selectbox(label='artista', options=artista_opcoes)

# Filtra o DataFrame apenas se um artista específico for selecionado
if artist != 'Todos':
    df_filtrado = df[df['Artist'] == artist]
else:
    df_filtrado = df

st.bar_chart(data=df_filtrado[df_filtrado['Stream'] > 1000000000], x='Track', y='Stream')
