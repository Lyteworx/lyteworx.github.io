#!/usr/bin/env python

import numpy as np
import pandas as pd
import pycountry
import plotly.express as px

gl_confirmed_path = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'
gl_death_path = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'
gl_c = pd.read_csv(gl_confirmed_path)
gl_d = pd.read_csv(gl_death_path)

df_con = pd.read_csv('data/country-and-continent-codes-list.csv')
continent_map = dict()
for row in df_con.itertuples():
    continent_map[row.Country_Name] = row.Continent_Name
continent_map.update({'US': 'North America', 'UK': 'Europe',
                      'Cabo Verde': 'Africa', 'Congo (Brazzaville)': 'Africa',
                      'Congo (Kinshasa)': 'Africa', 'Czechia': 'Europe',
                      'Diamond Princess': 'Asia', 'Eswatini': 'Africa',
                      'Korea, South': 'Asia', 'Kyrgyzstan': 'Asia',
                      'North Macedonia': 'Europe', 'Taiwan*': 'Asia',
                      'Laos': 'Asia', 'West Bank and Gaza': 'Asia',
                      'Kosovo': 'Europe', 'Burma': 'Asia',
                      'MS Zaandam': 'North America'})

c = gl_c.groupby('Country/Region').sum().iloc[:, 2:].unstack().reset_index()

d = gl_d.groupby('Country/Region').sum().iloc[:, 2:].unstack().reset_index()
df = pd.merge(c, d, on=['level_0', 'Country/Region'])
new_names = {'level_0': 'Date', 'Country/Region': 'Country',
             '0_x': 'Confirmed', '0_y': 'Deaths'}
df = df.rename(columns=new_names)

df['Date'] = pd.to_datetime(df['Date']).dt.strftime("%Y-%m-%d")
df = df.groupby(['Date', 'Country']).sum().reset_index() # combine duplicate rows
df['Death Rate'] = (df.Deaths / df.Confirmed * 100).fillna(1).round(2)
idx = df[df['Death Rate'] == 0].index
df.at[idx, 'Death Rate'] = 1  # controls the bubble size


def find_continent(country):
    for key, value in continent_map.items():
        if country in key:
            return value


df['Continent'] = df.Country.apply(find_continent)  # assign continent

idx = df[df['Confirmed'] < 0].index
df.at[idx, 'Confirmed'] = 0 # no negative cases allowed

idx = df[df['Deaths'] < 0].index
df.at[idx, 'Deaths'] = 0 # no negative deaths allowed

# people on Antarctica are social distancing enough.
idx = df[df.Continent == 'Antarctica'].index
df.drop(idx, inplace=True)

country_correction = {
    'Burma': 'Myanmar',
    'Congo (Brazzaville)': 'Republic of the Congo',
    'Congo (Kinshasa)': 'Congo, The Democratic Republic of the',
    'Korea, South': 'Korea, Republic of',
    'Laos': "Lao People's Democratic Republic",
    'Taiwan*': 'Taiwan',
    'West Bank and Gaza': 'Palestine, State of',
    }
for key, value in country_correction.items():
    idx = df[df.Country == key].index
    df.at[idx, 'Country'] = value

def assign_alpha(x):
    try:
        a = pycountry.countries.get(name=x).alpha_3
        return a
    except AttributeError:
        try:
            a = pycountry.countries.get(common_name=x).alpha_3
            return a
        except AttributeError:
            try:
                a = pycountry.countries.search_fuzzy(x)
                a = a[0].alpha_3
                return a
            except LookupError:
                print(f'No country data for {x}.')
                return x


for c in df.Country.unique():
    idx = df[df.Country == c].index
    df.at[idx, 'iso_alpha_3'] = assign_alpha(c)

max_list = list()
for c in df.Country.unique():
    max_list.append(df.Confirmed[df.Country == c].max())

q = 99
cmax = int(np.percentile(max_list, q))

fig = px.choropleth(
    df[df.Date >= '2020-02-14'],
    locations="iso_alpha_3",
    color="Confirmed",
    animation_frame='Date',
    animation_group='Country',
    hover_name="Country",
    color_continuous_scale=px.colors.diverging.Portland,
    range_color=[0,cmax],
    projection='natural earth',
    title=f'COVID-19 Confirmed Cases (scale maxed at {q}th percentile: {cmax:,})<br>'
          f'Source:<a href="https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data">'
          f'JHU CSSE COVID-19 Dataset</a>'
    )
fig.write_html('charts/global_confirmed_cases_map.html')

days = df.Date.unique()
fig = px.scatter(
    data_frame=df,
    x='Confirmed',
    y='Deaths',
    animation_frame='Date',
    animation_group='Country',
    size='Death Rate',
    color='Continent',
    hover_name='Country',
    size_max=100,
    title=f'COVID-19 Confirmed Cases<br>'
          f'Source:<a href="https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data">'
          f'JHU CSSE COVID-19 Dataset</a>',
    category_orders={'Day':days}
)
fig.update_layout(width=1200)
fig.write_html("charts/global_confirmed_cases_bubble_chart.html")


fig = px.scatter(
    data_frame=df,
    x='Confirmed',
    y='Deaths',
    animation_frame='Date',
    animation_group='Country',
    size='Death Rate',
    color='Country',
    hover_name='Country',
    facet_col='Continent',
    facet_col_wrap=3,
    size_max=75,
    title=f'COVID-19 Confirmed Cases<br>'
          f'Source:<a href="https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data">'
          f'JHU CSSE COVID-19 Dataset</a>',
    category_orders={'Day':days}
)
fig.update_layout(width=1200)
fig.write_html("charts/global_confirmed_cases_bubble_chart_per_continent.html")

def split_by_state(country, df):
    df = df[df.Country == country].copy()
    return df

def calc_growth_rate(df):
    #calc growth rate
    df['today'] = df.Confirmed.diff().fillna(0)
    df['yesterday'] = df.today.shift(1).fillna(method='ffill')
    df['growth_rate'] = (df['today'] / df['yesterday'] - 1).round(3)
    df['growth_rate'] = df['growth_rate'].replace([np.inf, -np.inf], np.nan)
    df['growth_rate'] = df['growth_rate'].fillna(method='ffill')
    # calc rolling growth rate
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date', drop=False)
    df = df.sort_index()
    df['rolling_growth_rate'] = df['growth_rate'].clip(-5,5).rolling('14d').mean().round(3)
    df['Date'] = df['Date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    return df

df_c = list()
for c in df.Country.unique():
    df_c.append(split_by_state(c, df))

new_dfs = list()
for d in df_c:
    new_dfs.append(calc_growth_rate(d))

sdn = pd.concat(new_dfs, ignore_index=True)
sdn.reset_index(drop=True)
sdn.to_csv('data/global_confirmed_growth_rate.csv', index=False)

fig = px.choropleth(
    sdn[(sdn.Date >= '2020-01-01') &
        (pd.to_datetime(sdn.Date) <= pd.to_datetime(sdn.Date.max()) - pd.Timedelta(days=1))],
    locations='iso_alpha_3',
    color='rolling_growth_rate',
    animation_frame='Date',
    animation_group='Country',
    hover_name="Country",
    hover_data=['Date', 'Confirmed', 'Deaths', 'today', 'yesterday',
                'growth_rate'],
    color_continuous_scale=px.colors.diverging.RdYlGn_r,
    color_continuous_midpoint=0,
    range_color=[-1,1],
    projection='natural earth',
    title=f'COVID-19 Confirmed Cases Rolling 14-Day Average Growth Rate<br>'
          f'Source: <a href="https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data">'
          f'JHU CSSE COVID-19 Dataset</a>'
    )
fig.update_layout(
    coloraxis_colorbar=dict(
        title='Rolling Growth Rate'
        )
    )
fig.write_html('charts/global_confirmed_cases_rolling_14-Day_average_growth_rate_map.html')

sdn[['Date', 'Confirmed', 'today', 'yesterday']][sdn.Country == 'US'].tail(20)
# little data backup never hurt anyone...
df.to_csv('data/scatter_global.csv', index=False)

df = pd.read_csv('https://covid.ourworldindata.org/data/owid-covid-data.csv')

us_true = df.location == 'United States'
date = df.date >= '2020-03-01'
us = df[us_true & date]

import plotly.graph_objects as go
from plotly.subplots import make_subplots
fig = make_subplots(rows=3, cols=2, specs=[[{},{"rowspan": 2}],
                                           [{}, None],
                                           [{"secondary_y": True,
                                                 "colspan": 2}, None]])
fig.add_trace(go.Bar(
    name='New Tests', x=us.date, y=us.new_tests, opacity=1),
    row=1, col=1)
fig.add_trace(go.Bar(
    name='New Cases', x=us.date, y=us.new_cases, opacity=1),
    row=2, col=1)
fig.add_trace(go.Scatter(
    name='Cases per test', x=us.date, y=us.new_cases / us.new_tests,
    opacity=0.6, mode='lines+markers'),
    row=1, col=2, )

fig.add_trace(go.Bar(
    name='New Tests (lower)', x=us.date, y=us.new_tests, opacity=1),
    row=3, col=1)
fig.add_trace(go.Bar(
    name='New Cases (lower)', x=us.date, y=us.new_cases, opacity=1),
    row=3, col=1)
fig.add_trace(go.Scatter(
    name='Cases per test (lower)', x=us.date, y=us.new_cases / us.new_tests,
    opacity=0.6, mode='lines+markers'),
    row=3, col=1, secondary_y=True)



fig.update_layout(
    barmode='group',
    title=f'Comparison of New Cases and Tests Administered<br>'
          f'Source: <a href="https://github.com/owid/covid-19-data/tree/master/public/data">'
          f'Data on COVID-19 (coronavirus) by Our World in Data</a> ('
          f'<a href="https://covid.ourworldindata.org/data/owid-covid-data.csv">CSV file</a>)',
    yaxis_title='New Cases',
)
fig.update_yaxes(title_text="New Tests",row=1, col=1)
fig.update_yaxes(title_text="New Cases",row=2, col=1)
fig.update_yaxes(title_text="New Cases/Tests",row=3, col=1)
fig.update_yaxes(title_text="New Cases per Test",row=1, col=2)
fig.update_yaxes(title_text="New Cases per Test",secondary_y=True, row=3, col=1)


fig.write_html('charts/united_states_cases_per_test.html')
