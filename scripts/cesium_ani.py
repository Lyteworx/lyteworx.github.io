import json
import random
import shapely
import pandas as pd
import numpy as np
import geopandas as gpd
import logging
import us
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.animation import FFMpegWriter
from matplotlib.dates import DateFormatter, WeekdayLocator, DayLocator, MONDAY
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime
from pathlib import Path

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
df_map = gpd.read_file(fp_c)

# logging.info(f'Flattening county multipolygon shapes.')
# df_temp = pd.DataFrame([])
# for i, v in df_map.iterrows():
#     if isinstance(v.geometry, shapely.geometry.multipolygon.MultiPolygon):
#         for p in list(v.geometry):
#             new_v = v.copy()
#             new_v.at['geometry'] = p
#             df_temp = df_temp.append(new_v, ignore_index=True)
#         df_map.drop(i, inplace=True)
# df_map = pd.concat([df_map, df_temp])
# df_map.reset_index(drop=True, inplace=True)
# del df_temp

# logging.info(f'Converting state map to EPSG 2163.')
# st_map = st_map.to_crs(epsg=3857)
logging.info(f'Converting county map to EPSG 4326.')
df_map = df_map.to_crs(epsg=4326)

us_confirmed_path = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
us_death_path = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'

logging.info(f'Loading confirmed cases: {us_confirmed_path}')
us_c = pd.read_csv(us_confirmed_path)
logging.info(f'Loaded cases with shape: {us_c.shape}')

logging.info(f'Loading death cases: {us_death_path}')
us_d = pd.read_csv(us_death_path)
logging.info(f'Loaded deaths with shape: {us_d.shape}')

logging.info(f'Dropping rows with out county names.')
us_c.drop(us_c[us_c.Admin2.isna()].index, inplace=True)
logging.info(f'Cases new shape: {us_c.shape}')
us_d.drop(us_d[us_d.Admin2.isna()].index, inplace=True)
logging.info(f'Deaths new shape: {us_d.shape}')

df_map['cid'] = df_map.GEO_ID.apply(lambda x: f'{str(x)[-5:]:0>5}')
us_c['cid'] = us_c.UID.apply(lambda x: f'{str(x)[-5:]:0>5}')
us_d['cid'] = us_d.UID.apply(lambda x: f'{str(x)[-5:]:0>5}')

c = us_c.groupby('cid').sum().iloc[:, 5:].unstack().reset_index()
d = us_d.groupby('cid').sum().iloc[:, 6:].unstack().reset_index()
cd = pd.merge(c, d, on=['level_0', 'cid'])
new_names = {'level_0': 'date', '0_x': 'confirmed', '0_y': 'deaths'}
cd = cd.rename(index=str, columns=new_names)
cd['date'] = pd.to_datetime(cd['date'])


logging.info(f'Dropping rows where cid starts with 70, 80, 88, 90, 99.')
for i in [70, 80, 88, 90, 99]:
    idx = cd[cd['cid'].str.startswith(str(i))].index
    cd.drop(idx, inplace=True)


logging.info(f'Adding state names to merged data frames.')
for row in cd.itertuples():
    st = row.cid[:2]
    try:
        cd.at[row.Index, 'state'] = us.states.lookup(st).name
    except AttributeError:
        logging.error(f'AttributeError: Cannot find state name for code: '
                      f'{row.Index, st}')

cond2 = cd.state == 'Virginia'

co = cd[cond2].copy()


def gen_poly_json(x, y, cnty, lsad, map_idx, name, enum=0):
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)
    coords = list()
    for lon, lat in zip(x, y):
        coords.append(lon)
        coords.append(lat)
        coords.append(0)
    coords_id = '_'.join([cnty, lsad, df_map.at[map_idx, 'STATE'],
                          'coords', str(enum)])
    p = f"""
{{
  id: "{coords_id}",
  name: "{name}",
  polygon: {{
    positions: {{
      cartographicDegrees: {coords},
      }},
    material: {{
      solidColor: {{
        color: {{
          rgba: [{red}, {green}, {blue}, 150],
          }},
        }},
      }},
    height: 0,
    extrudedHeight: 0,
  }},
}},
"""
    return coords_id, p


czml = ''
all_ids = list()

for cid in co.cid.unique():
    map_idx = df_map[df_map.cid == cid].index.values[0]
    county = df_map.at[map_idx, 'NAME']
    lsad = df_map.at[map_idx, 'LSAD'].lower()
    cnty = county.replace(' ', '_').lower()
    state = us.states.lookup(cid[:2]).name
    co_df = co[co.cid == cid]
    _id = '_'.join([cnty, lsad, df_map.at[map_idx, 'STATE'], 'cases'])
    name = ' '.join([county, lsad, state]).title()
    logging.info(f'Compiling data for: {name}')

    cases = list()
    for row in co_df.itertuples():
        cases.append(row.date.isoformat())
        cases.append(row.confirmed)
    d = f"""
  {{
  id: "{_id}",
  name: "{name + ' Data'}",
  properties: {{
    constant_property: true,
    cases: {{
      number: {cases}
      }},
    }},
  }},
"""
    czml += d
    try:
        x, y = df_map.at[map_idx, 'geometry'].exterior.coords.xy
        coords_id, p = gen_poly_json(x, y, cnty, lsad, map_idx, name)
        all_ids.append((_id, coords_id))
        czml += p
    except AttributeError:
        poly = list(df_map.at[map_idx, 'geometry'])
        for e, i in enumerate(poly):
            x, y = i.exterior.coords.xy
            coords_id, p = gen_poly_json(x, y, cnty, lsad, map_idx, name, e + 1)
            all_ids.append((_id, coords_id))
            czml += p

start = co.at[co.date.sort_values().index[0], 'date']
stop = co.at[co.date.sort_values().index[-1], 'date']
interval = '/'.join([start.isoformat(), stop.isoformat()])
doc_setup = f"""{{
    id: "document",
    name: "CZML Custom Properties",
    version: "1.0",
    clock: {{
        interval: "{interval}",
        currentTime: "{start.isoformat()}",
        multiplier: {int((stop - start).total_seconds() / 20)},
    }},
}},
"""

czml = 'var czml = [\n' + doc_setup + czml + '\n];'

# Building JS code
js_code = """
function scaleProperty(property, scalingFactor) {
  return new Cesium.CallbackProperty(function (time, result) {
    result = property.getValue(time, result);
    result = result * scalingFactor;
    return result;
  }, property.isConstant);
}
function updateDescription(property) {
  // returns a property that scales another property by a constant factor.
  return new Cesium.CallbackProperty(function (time, result) {
    result = property.getValue(time, result);
    result = "<p>Confirmed COVID-19 Cases: "+ Math.ceil(result) + "</p>";
    return result;
  }, property.isConstant);
}

function setExtrudedHeight() {"""

for e, (case_id, coord_id) in enumerate(all_ids):
    case_vars = f"""
  var property_{e} = dataSource.entities.getById("{case_id}").properties.cases;
  var {coord_id} = dataSource.entities.getById("{coord_id}");
  {coord_id}.polygon.extrudedHeight = scaleProperty(property_{e}, 10);
  {coord_id}.description = updateDescription(property_{e});
"""
    js_code += case_vars

js_code += """}

var viewer = new Cesium.Viewer("cesiumContainer", {
  shouldAnimate: true,
});

var dataSource = new Cesium.CzmlDataSource();


dataSource.load(czml);
viewer.dataSources.add(dataSource);
viewer.zoomTo(dataSource);
viewer.scene.debugShowFramesPerSecond = true;
setExtrudedHeight();
"""

js_code = czml + js_code

with open('virginia.js', 'w') as f:
    f.write(js_code)
logging.info('Done.')
