import streamlit as st
import openai

import openai
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv()) # Isso é útil para acessar informações sensíveis, como chaves de API, sem expô-las diretamente no código.
client = openai.OpenAI() # Cria uma instância do cliente OpenAI para interagir com a API.

st.header('Bem vindo ao e🎥')
tab1, tab2 = st.tabs(["Video", "Código"])