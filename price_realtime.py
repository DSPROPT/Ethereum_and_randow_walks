import csv
import os
from flask import Flask
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
import json
import pandas as pd
import numpy as np

# Kraken API function
def get_eth_price():
    url = "https://api.kraken.com/0/public/Ticker?pair=ETHEUR"
    response = requests.get(url)
    data = json.loads(response.text)
    return float(data['result']['XETHZEUR']['c'][0])  # This gets the current price

def write_eth_price_to_csv():
    # Check if file exists, write headers if it doesn't
    if not os.path.isfile('eth_price.csv'):
        with open('eth_price.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['datetime', 'price'])
    
    # Fetch and write price
    price = get_eth_price()
    with open('eth_price.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow([pd.Timestamp.now(), price])

def simulate_random_walk(df):
    log_returns = np.log(df['price'] / df['price'].shift(1))
    u = log_returns.mean()  # mean of log returns
    var = log_returns.var()  # variance of log returns
    stdev = log_returns.std()  # standard deviation of log returns

    t_intervals = len(df)  # time intervals
    iterations = 1  # number of simulations

    # Brownian motion
    drift = u - (0.5 * var)
    Z = np.random.standard_normal((t_intervals, iterations))
    daily_returns = np.exp(drift + stdev * Z)
    
    # Create a price list
    price_list = [df['price'].iloc[-1]]

    for i in range(1, t_intervals):
        price_list.append(float(price_list[i - 1] * daily_returns[i]))
    
    return pd.Series(price_list, index=df.index, name='random_walk')

server = Flask(__name__)
app = dash.Dash(__name__, server=server, url_base_pathname='/')

app.layout = html.Div(children=[
    html.H1(children='Desenvolvimento de um Rastreador de Preços de Ethereum com Python e Dash'),
    html.Img(src='/assets/my_logo.png', style={'height':'10%', 'width':'10%'}),
    html.Div(id='live-update-text'),
    dcc.Graph(
        id='live-graph', 
        animate=True, 
        config={
            'autosizable': True, 
            'scrollZoom': True, 
            'displayModeBar': True,
            'responsive': True
        }
    ),
    dcc.Interval(
        id='graph-update',
        interval=1*1000,
        n_intervals=0
    ),
])

@app.callback(
    Output('live-graph', 'figure'),
    [Input('graph-update', 'n_intervals')],
    [State('live-graph', 'figure')]
)
def update_graph_scatter(n, existing_figure):
    max_points = 86400  # maximum number of data points to keep

    # Write the current ETH price to CSV
    write_eth_price_to_csv()

    # Read the data from CSV
    df = pd.read_csv('eth_price.csv')
    
    # Keep the last 'max_points' points
    df = df.iloc[-max_points:]

    # If the dataframe is empty, initialize an empty plot
    if df.empty:
        return {
            'data': [{
                'x': [],
                'y': [],
                'type': 'scatter'
            }]
        }
    
    # Only generate random walk if there's enough data
    if len(df) >= 1000:
        random_walk = simulate_random_walk(df)
        df = df.join(random_walk)
        print("Dataframe after joining random walk: \n", df.tail())  # print last 5 rows of the dataframe

    figure = {
        'data': [
            {
                'x': df['datetime'],
                'y': df['price'],
                'type': 'scatter',
                'name': 'Actual Price'
            },
            {
                'x': df['datetime'] if 'random_walk' in df else [],
                'y': df['random_walk'] if 'random_walk' in df else [],
                'type': 'scatter',
                'name': 'Random Walk'
            }
        ],
        'layout': {
            'yaxis': {'range': [min(df[['price', 'random_walk']].min()), max(df[['price', 'random_walk']].max())]},
            'xaxis': {'range': [min(df['datetime']), max(df['datetime'])]},
            'title': 'ETH-EUR',
            'uirevision': pd.Timestamp.now(),
        }
    }
    return figure

@app.callback(Output('live-update-text', 'children'),
              Input('graph-update', 'n_intervals'))
def update_metrics(n):
    style = {'padding': '5px', 'fontSize': '16px'}
    price = get_eth_price()
    return [
        html.Span(f'Current Ethereum Price: {price} €', style=style),
    ]

if __name__ == '__main__':
    server.run(port=5004, debug=True)  # Changed port to 5004
