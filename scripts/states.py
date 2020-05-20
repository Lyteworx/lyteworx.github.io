import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import logging
import us
from matplotlib.animation import FFMpegWriter
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pathlib import Path

matplotlib.use("Agg")
plt.rcParams['animation.ffmpeg_path'] = \
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')

fp_s = r'..\data\gz_2010_us_040_00_5m\gz_2010_us_040_00_5m.shp'
fp_c = r'..\data\gz_2010_us_050_00_500k\gz_2010_us_050_00_500k.shp'

logging.info(f'Loading state map data ({fp_s})')
st_map = gpd.read_file(fp_s)

logging.info(f'Loading county map data ({fp_c})')
map_df = gpd.read_file(fp_c)

logging.info(f'Converting state map to EPSG 2163.')
st_map = st_map.to_crs(epsg=2163)
logging.info(f'Converting county map to EPSG 2163.')
map_df = map_df.to_crs(epsg=2163)

logging.info(f'Converting Alaska to EPSG 3467.')
st_map[st_map.STATE == '02'] = st_map[st_map.STATE == '02'].to_crs(epsg=3467)
map_df[map_df.STATE == '02'] = map_df[map_df.STATE == '02'].to_crs(epsg=3467)

logging.info(f'Converting Hawaii to EPSG 4135.')
st_map[st_map.STATE == '15'] = st_map[st_map.STATE == '15'].to_crs(epsg=4135)
map_df[map_df.STATE == '15'] = map_df[map_df.STATE == '15'].to_crs(epsg=4135)

# if not Path('../data/merged3857.pkl').exists():
us_confirmed_path = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
us_death_path = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'

logging.info(f'Loading confirmed cases: {us_confirmed_path}')
us_c = pd.read_csv(us_confirmed_path)

logging.info(f'Loading death cases: {us_death_path}')
us_d = pd.read_csv(us_death_path)

map_df['cid'] = map_df.GEO_ID.apply(lambda x: str(x)[-5:])
us_c['cid'] = us_c.UID.apply(lambda x: str(x)[-5:])
us_d['cid'] = us_d.UID.apply(lambda x: str(x)[-5:])

c = us_c.groupby('cid').sum().iloc[:, 5:].unstack().reset_index()
d = us_d.groupby('cid').sum().iloc[:, 6:].unstack().reset_index()
cd = pd.merge(c, d, on=['level_0', 'cid'])
new_names = {'level_0': 'date', '0_x': 'confirmed', '0_y': 'deaths'}
cd = cd.rename(index=str, columns=new_names)
cd['date'] = pd.to_datetime(cd['date'])

logging.info(f'Merging map data and metric data.')
merged = pd.merge(map_df, cd, on='cid')

    # merged.to_pickle('../data/merged3857.pkl')
# else:
    # merged = pd.read_pickle('../data/merged3857.pkl')

for state in merged.STATE.unique():
    st_name = us.states.lookup(state).name
    this_st_map = st_map[st_map.STATE == state]

    df = merged[merged.STATE == state]
    df = df[df.confirmed > 0]
    df.sort_values('date', inplace=True)

    logging.info(f'Creating animation for {st_name}.')
    metadata = dict(title=f'{st_name} COVID-19 Confirmed Cases',
                    artist='Matplotlib',
                    comment='Source: JHU CSSE COVID-19 Dataset')
    writer = FFMpegWriter(fps=len(df.date.unique()) // 15, metadata=metadata)

    fig, ax = plt.subplots(1, figsize=(10, 6))
    this_st_map.boundary.plot(linewidth=0.8, ax=ax, edgecolor='0.8')
    ax.axis('off')
    ax.set_title(f'{st_name} COVID-19 Confirmed Cases',
                 fontdict={'fontsize': '18', 'fontweight': '3'})

    div = make_axes_locatable(ax)
    cax = div.append_axes('bottom', '5%', '5%')
    # vmin = df.confirmed.min()
    vmax = df.confirmed.max()
    sm = plt.cm.ScalarMappable(cmap='Blues', norm=plt.Normalize(vmin=0, vmax=vmax))
    cbar = fig.colorbar(sm, orientation="horizontal",
                        fraction=0.036, pad=0.1, aspect=30, cax=cax)

    with writer.saving(fig, f'../figures/{st_name}.mp4', 150):
        src, cas = None, None
        for n, date in enumerate(df.date.unique()):
            cond2 = (df.date == date)
            this_plot = df[cond2].copy()

            total = this_plot.confirmed.sum()

            str_date = np.datetime_as_string(date, unit='D')
            if src:
                src.remove()
            src = ax.annotate(f'Source: JHU CSSE COVID-19 Dataset, {str_date}',
                        xy=(0.5, 0.2),
                        xycoords='figure fraction',
                        horizontalalignment='center',
                        verticalalignment='top',
                        fontsize=8, color='#555555')
            if cas:
                cas.remove()
            cas = ax.annotate(f'Cases: {total:,}',
                        xy=(0.1, 0.85),
                        xycoords='figure fraction',
                        horizontalalignment='left',
                        verticalalignment='top',
                        fontsize=10, color='#555555')
            vmax = this_plot.confirmed.max()
            sm = plt.cm.ScalarMappable(cmap='Blues',
                                       norm=plt.Normalize(vmin=0, vmax=vmax))
            cax.cla()
            fig.colorbar(sm, orientation="horizontal",
                                fraction=0.036, pad=0.1, aspect=30, cax=cax)

            this_plot.plot(column='confirmed', cmap='Blues', linewidth=0.8,
                           ax=ax, edgecolor='0.8')
            logging.debug(f'Grabbing frame: {n + 1}')
            writer.grab_frame()
