from typing import Iterable
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount


class insights_meta:
    """
    Wrapper simples para Insights da Meta Ads (Facebook Marketing API).

    Recursos:
      - Construtor com credenciais explícitas ou via variáveis de ambiente
      - Método get_insights com paginação automática
      - Geração de linhas por dia (time_increment) e nível (ad/adset/campaign/account)
      - Retorno como lista de dicts e, opcionalmente, DataFrame (se pandas instalado)

    Variáveis de ambiente esperadas (quando usando `from_env()`):
      - META_APP_ID
      - META_APP_SECRET
      - META_ACCESS_TOKEN
      - META_AD_ACCOUNT_ID
    """
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        access_token: str,
        ad_account_id: str,
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = access_token
        

        FacebookAdsApi.init(
            app_id=self.app_id,
            app_secret=self.app_secret,
            access_token=self.access_token,
        )
        self.account = AdAccount(ad_account_id)

    # --------- API principal ---------
    def get_insights(
        self,
        fields: Iterable[str],
        *,
        level: str = "ad",  # "account" | "campaign" | "adset" | "ad"
        since: str,
        until: str,
        time_increment: int = 1,    # 1 = por dia; "all_days" = agregado no período
        limit: int = 500,
    ):
        """
        Busca insights com paginação automática e retorna lista de dicionários ou DataFrame.

        Exemplo de campos:
            ["date_start","campaign_name","adset_name","ad_name","spend","impressions","reach","inline_link_clicks"]

        Parâmetros úteis:
          - level: nível de agregação ("ad", "adset", "campaign", "account")
          - since/until: datas (str 'YYYY-MM-DD', date, ou datetime). Ajuste automático para datas inválidas (ex.: 2025-09-31 -> 2025-09-30)
          - time_increment: 1 (por dia), N (a cada N dias) ou "all_days"
          - breakdowns: ex. ["publisher_platform","platform_position"]
          - filtering: filtros no padrão da API
          - extra_params: dict com parâmetros adicionais aceitos pela API
          - max_pages: para limitar a paginação (debug)

        Raises:
            FacebookRequestError em falhas da API
            ValueError em parâmetros inválidos
        """
        fields = list(fields)
        if not fields:
            raise ValueError("Informe ao menos um campo em `fields`.")

        params = {
            "level": level,
            "time_range": {"since": f'{since}', "until": f'{until}'},
            "time_increment": time_increment,
            "limit": limit,
        }

        
        cursor = self.account.get_insights(fields=fields, params=params)
        rows = [r.export_all_data() for r in cursor]

        while cursor.load_next_page():
            rows.extend([r.export_all_data() for r in cursor])
        
        return rows