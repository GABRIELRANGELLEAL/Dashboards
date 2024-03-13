# ======= imports ========= #
import dash
from dash import html, dcc
from dash.dependencies import Input, Output

import pandas as pd
import numpy as np

import plotly.express as px
import plotly.graph_objects as go

# ======== ETL =========== # 

df = pd.read_csv('https://raw.githubusercontent.com/GABRIELRANGELLEAL/Data-analises-projects/Supermarket_dash/supermarket_sales.csv')
df['Date'] = pd.to_datetime(df['Date'])


app = dash.Dash(__name__)

# ======== Layout =========== # 
'''
https://dash.plotly.com/dash-html-components
https://dash.plotly.com/dash-core-components

'''

app.layout = html.Div(children=[
    html.H5("Cities"),
    dcc.Checklist(
        df.City.unique(),
        df.City.unique(),
        inline=True,
        id = 'checklist_1'
    ),
    html.H5("Analysis variable"),
    dcc.RadioItems(
        ["gross income", "Rating"],
        "gross income",
        id = 'radioitems_1'
    ),
    dcc.Graph(
        id = 'city_time'
    ),
        dcc.Graph(
        id = 'payment_time'
    ),
        dcc.Graph(
        id = 'income_product'
    )
])

# ======== Callbacks =========== # 
'''
all fuctions bellow the callback are going to recieve these two inputs as parameters
And de return of the all fuctions will modify the outputs
'''
@app.callback(
    [
        Output('city_time', 'figure'),
        Output('payment_time', 'figure'),
        Output('income_product', 'figure')
    ], #outputs
    [
        Input('checklist_1','value'),
        Input('radioitems_1','value')
    ] #inputs
)

def render_graphs(cities,variable):
    operation = np.sum if variable == 'gross income' else np.mean
    df_filtered = df[df['City'].isin(cities)]
    # === building data frames == # 
    df_city = df_filtered.groupby("City")[variable].apply(operation).to_frame().reset_index()
    df_payment = df_filtered.groupby("Payment")[variable].apply(operation).to_frame().reset_index()
    df_product_income = round(df_filtered.groupby(["Product line","City"])[variable].apply(operation).to_frame().reset_index(),2)
    
    # === building graphs using plotly express == #
    fig_city = px.bar(df_city, x = "City", y=variable)
    fig_payment = px.bar(df_payment, x = "Payment", y=variable)
    fig_product_inome = px.bar(df_product_income, x = variable, y='Product line', color = 'City', orientation = 'h', barmode = 'group')

    fig_city.update_layout(margin=dict(l = 0,r=0,t=20,b=20),height = 200)
    fig_payment.update_layout(margin=dict(l = 0,r=0,t=20,b=20),height = 200)
    fig_product_inome.update_layout(margin=dict(l = 0,r=0,t=20,b=20),height = 800)

    return fig_city, fig_payment, fig_product_inome
# ======== Run =========== # 
if __name__ == '__main__':
    app.run_server(debug = True)