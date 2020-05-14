import pandas as pd
import numpy as np
import us
import os
import subprocess
from pathlib import Path
import plotly.express as px

os.chdir('../data')
# cmd = ['git', 'pull', 'https://github.com/mdcollab/covidclinicaldata.git']
cmd = ['git', 'submodule,' 'update', '--remote', '--merge']
out = subprocess.run(cmd, stdout=subprocess.PIPE)
print(out.stdout.decode())

data_path = Path().joinpath('covidclinicaldata/data')

df = pd.DataFrame([])
for csv in data_path.glob('*.csv'):
    dft = pd.read_csv(csv)
    df = pd.concat([df, dft])

os.chdir('../scripts')

df = df.rename(columns={'temperature': 'temperature_C'})
df['temperature_F'] = df['temperature_C'] * 9 / 5 + 32
num_cols = []
bool_cols = ['high_risk_exposure_occupation',
       'high_risk_interactions', 'diabetes', 'chd', 'htn', 'cancer', 'asthma',
       'copd', 'autoimmune_dis', 'ctab', 'labored_respiration', 'rhonchi',
       'wheezes', 'cough', 'fever', 'sob',
       'diarrhea', 'fatigue', 'headache', 'loss_of_smell', 'loss_of_taste',
       'runny_nose', 'muscle_sore', 'sore_throat']

fig = px.histogram(
    data_frame=df,
    x='temperature_F',
    color='covid19_test_results',
    marginal='rug',
    hover_data=['age', 'high_risk_exposure_occupation',
       'high_risk_interactions', 'diabetes', 'chd', 'htn', 'cancer', 'asthma',
       'copd', 'autoimmune_dis'],
    title='COVID-19 Temperature Histogram<br>'
          'Source:<a href="https://github.com/mdcollab/covidclinicaldata">'
          'Coronavirus Disease 2019 (COVID-19) Clinical Data Repository</a>'
    )
fig.write_html('../charts/clinical_temperature_histogram.html')


corr_cols = ['age', 'temperature_F', 'pulse', 'sys', 'dia', 'rr',
       'sats', 'days_since_symptom_onset']
corr = df[corr_cols].corr()
fig = px.imshow(
    corr,
    x=corr_cols,
    y=corr_cols,
    color_continuous_scale=px.colors.diverging.Picnic,
    color_continuous_midpoint=0

    )
# fig.write_html('../charts/numerical_symptom_correlation_matrix.html')


for c in bool_cols:
    idx = df[df[c] == True].index
    df.at[idx, c] = 1
    idx = df[df[c] == False].index
    df.at[idx, c] = -1
    df[c] = df[c].fillna(0)

bool_corr_pos = df[bool_cols][df.covid19_test_results == 'Positive'].corr()
bool_corr_pos = pd.melt(bool_corr_pos.reset_index(), id_vars='index')
bool_corr_pos.columns = ['x', 'y', 'value']

bool_corr_neg = df[bool_cols][df.covid19_test_results == 'Negative'].corr()
bool_corr_neg = pd.melt(bool_corr_neg.reset_index(), id_vars='index')
bool_corr_neg.columns = ['x', 'y', 'value']

fig = px.scatter(
    bool_corr_pos,
    x='x',
    y=bool_corr_pos['y'],
    size=bool_corr_pos['value'].fillna(0).abs() * 500,
    symbol_sequence=['square'],
    color=bool_corr_pos['value'].abs(),
    title='COVID-19 Symptom Correlation for testing <em>POSITIVE</em>.<br>'
          'Source:<a href="https://github.com/mdcollab/covidclinicaldata">'
          'Coronavirus Disease 2019 (COVID-19) Clinical Data Repository</a>',
    )
fig.update_xaxes(showgrid=True, ticks='outside', tickson='boundaries',
                 scaleratio=1, scaleanchor='y', title_text='symptoms',
                 tickangle=30)
fig.update_yaxes(showgrid=True, ticks='outside', tickson='boundaries',
                 scaleratio=1, title_text='symptoms')
fig.write_html('../charts/covid-19_positive_symptom_correlation_matrix.html')


fig = px.scatter(
    bool_corr_neg,
    x='x',
    y=bool_corr_neg['y'],
    size=bool_corr_neg['value'].fillna(0).abs() * 500,
    symbol_sequence=['square'],
    color=bool_corr_neg['value'].abs(),
    title='COVID-19 Symptom Correlation for testing <em>NEGATIVE</em>.<br>'
          'Source:<a href="https://github.com/mdcollab/covidclinicaldata">'
          'Coronavirus Disease 2019 (COVID-19) Clinical Data Repository</a>',
    )
fig.update_xaxes(showgrid=True, ticks='outside', tickson='boundaries',
                 scaleratio=1, scaleanchor='y', title_text='symptoms',
                 tickangle=30)
fig.update_yaxes(showgrid=True, ticks='outside', tickson='boundaries',
                 scaleratio=1, title_text='symptoms')
fig.write_html('../charts/covid-19_negative_symptom_correlation_matrix.html')

import plotly.graph_objects as go
from plotly.subplots import make_subplots
fig = make_subplots(rows=1, cols=2, specs=[[{},{}]], shared_yaxes=True)

fig.add_trace(go.Scatter(
    name='test negative',
    showlegend=False,
    x=bool_corr_neg['x'],
    y=bool_corr_neg['y'],
    mode='markers',
    marker=dict(symbol='square',
                size=bool_corr_pos['value'].fillna(0).abs() * 25,
                color=bool_corr_pos['value'].abs(),
                colorscale='blues',
                )
    ), row=1, col=1)

fig.add_trace(go.Scatter(
    name='test positive',
    showlegend=False,
    x=bool_corr_pos['x'],
    y=bool_corr_pos['y'],
    mode='markers',
    marker=dict(symbol='square',
                size=bool_corr_pos['value'].fillna(0).abs() * 25,
                color=bool_corr_pos['value'].abs(),
                colorscale='reds',
                )
    ), row=1, col=2)


fig.update_xaxes(showgrid=True, ticks='outside', tickson='boundaries',
                 scaleratio=1, scaleanchor='y',
                 tickangle=30)
fig.update_yaxes(showgrid=True, ticks='outside', tickson='boundaries',
                 scaleratio=1)

fig.update_layout(
    title=dict(
        text='Symptom Correlation: Blue test negative, Red test positive<br>'
             'Source:<a href="https://github.com/mdcollab/covidclinicaldata">'
             'Coronavirus Disease 2019 (COVID-19) Clinical Data Repository</a>'
        )
    )
fig.write_html('../charts/covid-19_symptom_correlation_matrix.html')
