import pandas as pd
import streamlit as st
import json
import io
import openai
import tabulate
import os
from datetime import date
from dotenv import load_dotenv, find_dotenv
from  meta_adds_connect import insights_meta as im

_ = load_dotenv(find_dotenv())

APP_ID = os.getenv("META_APP_ID")
APP_SECRET = os.getenv("META_APP_SECRET")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")

client = openai.OpenAI()

# =========================================================
# ========== Helpers =========
# =========================================================
def format_df_for_markdown(df: pd.DataFrame, max_rows=200, max_cols=30, float_round=4) -> pd.DataFrame:
    """
    - Limita linhas/colunas para não gerar textos enormes
    - Arredonda floats para reduzir "ruído" de dígitos
    """
    # limita colunas
    if df.shape[1] > max_cols:
        df = df.iloc[:, :max_cols].copy()

    # limita linhas
    if len(df) > max_rows:
        df = df.head(max_rows).copy()

    # arredonda floats
    for c in df.select_dtypes(include="number").columns:
        df[c] = df[c].round(float_round)

    return df

def df_to_md_bytesio(df: pd.DataFrame, file_basename: str) -> io.BytesIO:
    """
    Converte um DataFrame em Markdown (tabela) e retorna como BytesIO ".md".
    """
    df_md = format_df_for_markdown(df)
    md_text = df_md.to_markdown(index=False)
    # título e dica de truncamento
    md_full = f'''
        # {file_basename}
        _Tabela convertida automaticamente para Markdown._
        {md_text}
    '''
    bio = io.BytesIO(md_full.encode("utf-8"))
    bio.name = f"{file_basename}.md"   # extensão suportada pelo file_search
    bio.seek(0)
    return bio

def csv_to_md_bytesio(uploaded) -> io.BytesIO:
    uploaded.seek(0)
    df = pd.read_csv(uploaded)  # ajuste sep=... se necessário
    base = uploaded.name.rsplit(".", 1)[0]
    return df_to_md_bytesio(df, base)

def excel_to_md_bytesio(uploaded) -> io.BytesIO:
    uploaded.seek(0)
    # lê a primeira sheet por padrão; se quiser, liste as sheets e concatene
    df = pd.read_excel(uploaded)
    base = uploaded.name.rsplit(".", 1)[0]
    return df_to_md_bytesio(df, base)

def to_bytesio_with_name(uploaded) -> io.BytesIO:
    """
    Para PDFs já suportados nativamente.
    """
    data = uploaded.read()
    bio = io.BytesIO(data)
    bio.name = uploaded.name
    bio.seek(0)
    return bio

# =========================================================
# ========== Aba Input your data =========
# =========================================================

def import_data():
    st.subheader("Upload e Indexação")
    vs = client.vector_stores.create(name="docs_sessao_local")
    st.write("Vector Store criado:", vs.id)
    st.session_state["vs_id"] = vs.id  # só guarda o ID

    uploaded_files = st.file_uploader(
        "Escolha arquivos (PDF, CSV, Excel) — CSV/Excel serão convertidos para Markdown",
        type=["pdf", "csv", "xlsx", "xls"],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.write(f"Arquivos recebidos: {[uf.name for uf in uploaded_files]}")
        success, failed = 0, 0

        for uf in uploaded_files:
            name_lower = uf.name.lower()

            if name_lower.endswith(".pdf"):
                fs = to_bytesio_with_name(uf)
            elif name_lower.endswith(".csv"):
                fs = csv_to_md_bytesio(uf)
            elif name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
                fs = excel_to_md_bytesio(uf)
            else:
                st.warning(f"Pulado: {uf.name} (tipo não suportado)")
                continue

            try:
                batch = client.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vs.id,
                    files=[fs]
                )
                st.write(f"✅ Indexado: {fs.name} | status: {getattr(batch, 'status', 'desconhecido')}")
                success += 1
            except Exception as e:
                st.error(f"❌ Falha ao indexar {fs.name}: {e}")
                failed += 1
            finally:
                try:
                    fs.close()
                except:
                    pass
        st.write(f"Resumo: Sucesso={success} | Falhas={failed}")

# =========================================================
# ========== Aba Report e Insights =========
# =========================================================
def create_report():
    st.subheader("Report and insights")
    # ---------------------------
    # BOTÃO QUE ATIVA AS DATAS
    # ---------------------------
    # Usamos st.session_state para guardar variáveis entre "reruns" do Streamlit.
    # show_dates: controla se as caixas de data devem aparecer
    # date_range: dicionário para armazenar as duas datas escolhidas
    if "show_dates" not in st.session_state:
        st.session_state.show_dates = False
    if "date_range" not in st.session_state:
        st.session_state.date_range = {"start": None, "end": None}

    # Quando o botão é clicado, o Streamlit dá um "rerun".
    # Se o clique for detectado (True), ativamos o flag para mostrar os inputs.
    if st.button("Selecionar período"):
        st.session_state.show_dates = True

    # Aqui renderizamos duas caixas de data lado a lado (colunas).
    # Também já salvamos os valores escolhidos no session_state.
    if st.session_state.show_dates:
        col1, col2 = st.columns(2)
        with col1:
            # date_input retorna um objeto date
            start = st.date_input("Data inicial", value=date.today())
        with col2:
            end = st.date_input("Data final", value=date.today())

        # Salva no estado global para reutilizar em qualquer parte do app
        st.session_state.date_range["start"] = start
        st.session_state.date_range["end"] = end
    if start and end:
        start_str = start.isoformat()
        end_str   = end.isoformat()
    # mostrando range date pro usário
    # Basta acessar st.session_state.date_range["start"] e ["end"] onde precisar.
    if st.session_state.date_range["start"] and st.session_state.date_range["end"]:
        st.write(
            f"Você selecionou: "
            f"{st.session_state.date_range['start']} → {st.session_state.date_range['end']}"
        )
    # ----------------------------------------
    # extrainddo dados da api e fazendo  relatório
    # ----------------------------------------
    if st.button("Gerar relatório"):
        # valida se temos um vector store disponível
        vs_id = st.session_state.get("vs_id")
        meta = im(APP_ID, APP_SECRET, ACCESS_TOKEN, AD_ACCOUNT_ID)
        fields = ["date_start","campaign_name","adset_name","ad_name","spend","impressions","reach","inline_link_clicks"]
        dados = meta.get_insights(fields = fields, since = f'{start_str}', until=f'{end_str}',time_increment = 'all_days')
        if dados:
            try:
                resp = client.responses.create(
                    model="gpt-4.1-mini",  # modelo de texto compatível com tools
                    input=[
                        {
                            "role": "developer",
                            "content": f'''
                                Você receberá no user input uma lista de dicionários contendo resultados de campanhas do cliente. 
                                Atue como um **analista de marketing de dados sênior** e produza um **report estruturado em Markdown** no seguinte formato: 
                                📊 Reporte de Performance – Campanhas 
                                    1. Resumo Executivo  
                                        - 🔥 Destaque os **melhores desempenhos** (com métricas CTR, CPC, CPM, cliques) 
                                        - ❌ Destaque os **piores desempenhos** 
                                    2. Recomendações 
                                        - 💰 Sugira **alocação de budget** (onde investir mais e onde reduzir no formato bullet points) 
                                        - 🧪 Sugira **testes A/B práticos** (criativos, públicos, LPs, etc.) 
                                Regras: 
                                    - Use métricas por criativo/adset/campanha quando fizer sentido. 
                                    - Retorne **sempre formatado em Markdown**, com ícones e divisórias para ficar visual. 
                                    - O texto deve ter no máximo **2–3 blocos curtos por seção**.
                            '''
                        },
                        {
                            "role": "user",
                            "content": [
                                # dados como JSON em texto:
                                {"type": "input_text", "text": json.dumps(dados, ensure_ascii=False)}
                            ]
                        }
                    ],
                )
                st.subheader("Relatório")
                st.text(resp.output_text)

            except Exception as e:
                st.error(f"Erro ao gerar relatório: {e}")
    #     elif not vs_id:
    #         st.warning("Nenhum documento indexado nesta sessão. Vá para a aba 'Input your data' e suba arquivos.")
    #         return

    #     try:
    #         resp = client.responses.create(
    #             model="gpt-5-nano",  # modelo de texto compatível com tools
    #             input=[
    #                 {
    #                     "role": "developer",
    #                     "content": f"{developer_input}"
    #                 },
    #                 {
    #                     "role": "user",
    #                     "content": f"{user_input}"
    #                 }
    #             ],
    #             tools=[{
    #                 "type": "file_search",
    #                 "vector_store_ids": [vs_id], 
    #                 # opcional:
    #                 # "max_num_results": 8,
    #                 # "filters": {"type":"and","filters":[{"type":"eq","key":"author","value":"..."}]}
    #             }]
    #         )
    #         st.subheader("Relatório")
    #         st.write(resp.output_text)

    #     except Exception as e:
    #         st.error(f"Erro ao gerar relatório: {e}")
    # # ----------------------------------------
    # # chat
    # # ----------------------------------------
    # developer_input = 'Gere um resumo executivo (10 bullets) dos meus documentos e perguntas, com insights acionáveis'
    
    # user_input = st.text_area(
    #     "Escreva sua pergunta/pedido:",
    #     value="pergunte algo para o seus dados", # valor default 
    #     height=140
    # )

def test_tab():
    st.markdown(
        """
        # 📊 Reporte de Performance – Campanhas  

        ---

        ## 1. Resumo Executivo  

        - 🔥 **Melhores desempenhos**
        - **AD17 (LP02)** na campanha **Vendas BCP Quentes**  
            - CTR ≈ **1,84%** (525 cliques / 28.570 impressões)  
            - CPC ≈ **R$0,75** (R$392,94 / 525 cliques)  
            - CPM ≈ **R$13,76**  
        - **CTA BCP - 3 Erros mais comuns** na campanha **Vendas BCP Quentes**  
            - CTR ≈ **1,99%** (255 cliques / 12.838 impressões)  
            - CPC ≈ **R$0,69** (R$175,13 / 255 cliques)  
            - CPM ≈ **R$13,64**  

        - ❌ **Piores desempenhos**
        - **AD03** na campanha **Vendas BCP Frios**  
            - CTR ≈ **1,06%** (4 cliques / 378 impressões)  
            - CPC ≈ **R$2,51** (R$10,06 / 4 cliques)  
            - CPM ≈ **R$26,62**  
        - **AD04** na campanha **Vendas BCP Frios**  
            - CTR ≈ **1,40%** (5 cliques / 357 impressões)  
            - CPC ≈ **R$1,70** (R$8,49 / 5 cliques)  
            - CPM ≈ **R$23,78**  

        ---

        ## 2. Recomendações  

        - 💰 **Alocação de Budget**  
        - Investir mais em **AD17 (LP02)** e **CTA BCP - 3 Erros mais comuns** (alto CTR e CPC eficiente).  
        - Reduzir investimento em criativos da linha **Frias** (baixa entrega e custo alto por clique).  

        - 🧪 **Testes, ideias e melhorias**  
        - **Criativos**: explorar novos formatos de vídeo com CTA mais claros (especialmente nas campanhas Frias).  
        - **Públicos**: manter o target de engajados e seguidores, mas testar segmentações lookalike e de interesse complementar.  
        - **Landing Pages**: otimizar LPs dos anúncios com baixo CTR, reforçando clareza da proposta e tempo de carregamento.  

        ---
        """

    )

# =========================================================
# ========== Run App =========
# =========================================================

def main():
    st.header('Mkt Analytics Tool')
    tab1, tab2, tab3 = st.tabs(["Input your data", "Report and insights", "test"])
    with tab1:
        import_data()
    with tab2:
        create_report()
    with tab3:
        test_tab()

if __name__ == '__main__':
    main()
