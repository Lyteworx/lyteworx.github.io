#%%

import numpy as np
import us
import pandas as pd
import os
import subprocess
from pathlib import Path
import plotly.express as px

us_confirmed_path = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
us_death_path = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'

us_c = pd.read_csv(us_confirmed_path)
us_d = pd.read_csv(us_death_path)

a = us_c.groupby('Province_State').sum().iloc[:, 5:].unstack().reset_index()
b = us_d.groupby('Province_State').sum().iloc[:, 6:].unstack().reset_index()
scatter_data = pd.merge(a, b, on=['level_0', 'Province_State'])
new_names = {'level_0': 'Date', 'Province_State': 'State',
             '0_x': 'Confirmed', '0_y': 'Deaths'}
scatter_data = scatter_data.rename(columns=new_names)

scatter_data['Date'] = pd.to_datetime(scatter_data['Date']).dt.\
    strftime("%Y-%m-%d")
days = scatter_data.Date[scatter_data['Confirmed'] > 0].unique()

scatter_data['Death Rate'] = (scatter_data.Deaths /
                        scatter_data.Confirmed * 100).fillna(1).round(2)
idx = scatter_data[scatter_data['Death Rate'] == 0].index
scatter_data.at[idx, 'Death Rate'] = 1

idx = scatter_data[scatter_data['Confirmed'] < 0].index
scatter_data.at[idx, 'Confirmed'] = 0

idx = scatter_data[scatter_data['Deaths'] < 0].index
scatter_data.at[idx, 'Deaths'] = 0


#%%

fig = px.scatter(
    data_frame=scatter_data,
    x='Confirmed',
    y='Deaths',
    animation_frame='Date',
    animation_group='State',
    size='Death Rate',
    color='State',
    hover_name='State',
    size_max=100,
    title='COVID-19 United States Pandemic',
    category_orders={'Day':days}
)
fig.update_layout(width=1200)
fig.write_html("../charts/united_states_bubble_chart.html")

#%%

pop = pd.read_csv('../data/us_population.csv').set_index('state')
max_confirmed = list()
for s in scatter_data.State.unique():
    max_confirmed.append(scatter_data.Confirmed[scatter_data.State == s].max())
    idx = scatter_data[scatter_data.State == s].index
    try:
        scatter_data.at[idx, 'state_abbr'] = us.states.lookup(s).abbr
        scatter_data.at[idx, 'population'] = pop.population.loc[s]
    except KeyError:
        print(f'Cannot find population for {s}.')
    except AttributeError:
        print(f'Cannot find abbreviation for {s}.')
scatter_data['Confirmed per M'] = \
    (scatter_data.Confirmed / (scatter_data.population / 1000000)).fillna(0)

max_confirmed_norm = list()
for s in scatter_data.State.unique():
    max_confirmed_norm.append(scatter_data['Confirmed per M']
                         [scatter_data.State == s].max())

scatter_data.to_csv('../data/scatter_us.csv', index=False)

#%%

q = 95
cmax = int(np.percentile(max_confirmed, q))

fig = px.choropleth(
    scatter_data[scatter_data.Date >= '2020-03-14'],
    locationmode='USA-states',
    locations="state_abbr",
    color="Confirmed",
    animation_frame='Date',
    animation_group='State',
    hover_name="State",
    color_continuous_scale=px.colors.diverging.Portland,
    range_color=[0,cmax],
    projection='albers usa',
    title=f'COVID-19 Confirmed Cases (scale maxed at {q}th percentile: {cmax:,})<br>'
          f'Source:<a href="https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data">'
          f'JHU CSSE COVID-19 Dataset</a>'
    )

fig.write_html('../charts/united_states_confirmed_cases_map.html')

#%%

q = 85
cmax = np.percentile(max_confirmed_norm, q)

fig = px.choropleth(
    scatter_data[scatter_data.Date >= '2020-03-14'],
    locationmode='USA-states',
    locations='state_abbr',
    color='Confirmed per M',
    animation_frame='Date',
    animation_group='State',
    hover_name="State",
    hover_data=scatter_data.columns,
    color_continuous_scale=px.colors.diverging.Portland,
    range_color=[0,cmax],
    projection='albers usa',
    title=f'COVID-19 Confirmed Cases per Million (scale maxed at {q}th percentile: {cmax:.0f})<br>'
          f'Source: <a href="https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data">'
          f'JHU CSSE COVID-19 Dataset</a>'
    )

fig.write_html('../charts/united_states_confirmed_cases_per_million_map.html')

#%% growth rate

def split_by_state(state, df):
    df = df[df.State == state].copy()
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

df_s = list()
for s in scatter_data.State.unique():
    df_s.append(split_by_state(s, scatter_data))

new_dfs = list()
for d in df_s:
    new_dfs.append(calc_growth_rate(d))

sdn = pd.concat(new_dfs, ignore_index=True)
sdn.reset_index(drop=True)
sdn.to_csv('../data/us_confirmed_growth_rate.csv', index=False)

#%%

fig = px.choropleth(
    sdn[(sdn.Date > '2020-03-14') &
        (pd.to_datetime(sdn.Date) <= pd.to_datetime(sdn.Date.max()) - pd.Timedelta(days=1))],
    locationmode='USA-states',
    locations='state_abbr',
    color='growth_rate',
    animation_frame='Date',
    animation_group='State',
    hover_name="State",
    hover_data=['Date', 'Confirmed', 'Deaths', 'today', 'yesterday',
                'growth_rate'],
    color_continuous_scale=px.colors.diverging.RdYlGn_r,
    color_continuous_midpoint=0,
    range_color=[-1,1],
    projection='albers usa',
    title=f'COVID-19 Confirmed Cases Growth Rate<br>'
          f'Source: <a href="https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data">'
          f'JHU CSSE COVID-19 Dataset</a>'
    )

fig.write_html('../charts/united_states_confirmed_cases_growth_rate_map.html')

#%%

fig = px.choropleth(
    sdn[(sdn.Date >= '2020-03-12') &
        (pd.to_datetime(sdn.Date) <= pd.to_datetime(sdn.Date.max()) - pd.Timedelta(days=1))],
    locationmode='USA-states',
    locations='state_abbr',
    color='rolling_growth_rate',
    animation_frame='Date',
    animation_group='State',
    hover_name="State",
    hover_data=['Date', 'Confirmed', 'Deaths', 'today', 'yesterday',
                'growth_rate'],
    color_continuous_scale=px.colors.diverging.RdYlGn_r,
    color_continuous_midpoint=0,
    range_color=[-1,1],
    projection='albers usa',
    title=f'COVID-19 Confirmed Cases Rolling 14-Day Average Growth Rate<br>'
          f'Source: <a href="https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data">'
          f'JHU CSSE COVID-19 Dataset</a>'
    )
fig.update_layout(
    coloraxis_colorbar=dict(
        title='Rolling Growth Rate'
        )
    )
fig.write_html('../charts/united_states_confirmed_cases_rolling_14-Day_average_growth_rate_map.html')

#%%

df_state_weekly = pd.DataFrame([])
for state in sdn.State.unique():
    df = sdn[sdn.State == state].copy()
    df['week_ago'] = df.today.shift(7)
    df['today_7day_sum'] = df.today.rolling(7).mean()
    df['week_ago_7day_sum'] = df.week_ago.rolling(7).mean()
    df['mean_percent_weekly_change'] \
        = (df['today_7day_sum'] - df['week_ago_7day_sum']) / df['today_7day_sum'] * 100
    df_state_weekly = df_state_weekly.append({'state': state,
                            'mean_percent_weekly_change':
                                df['mean_percent_weekly_change'].iloc[-1]},
                           ignore_index=True)
# print(df_state_weekly)
import plotly.graph_objects as go

df_bar = df_state_weekly.copy()
df_bar.rename(columns={'mean_percent_weekly_change': 'pwc'}, inplace=True)

fig = go.Figure()
fig.add_trace(
    go.Bar(
        name='increasing',
        x=df_bar['state'][df_bar['pwc'] > 0],
        y=df_state_weekly['mean_percent_weekly_change'][df_bar['pwc'] > 0],
        ),
    )
fig.add_trace(
    go.Bar(
        name='decreasing',
        x=df_bar['state'][df_bar['pwc'] < 0],
        y=df_state_weekly['mean_percent_weekly_change'][df_bar['pwc'] < 0],
        )
    )
