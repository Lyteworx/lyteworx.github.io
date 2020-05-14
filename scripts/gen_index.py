from pathlib import Path
from datetime import datetime

html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1" charset="UTF-8">
    <title>COVID-19 Analysis</title>
    <style>
    table {
      border-collapse: collapse;
      border-spacing: 0;
      width: 100%;
      border: 1px solid #ddd;
    }
    
    th, td {
      text-align: left;
      padding: 4px;
    }
    
    tr:nth-child(even) {
      background-color: #f2f2f2;
    }
    </style>
</head>
<body>
<table>
<tr>
    <th>Last Updated</th>
    <th>Chart Name</th>
</tr>
"""
for p in Path('charts').glob('*.html'):
    dtg = datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
    name = ' '.join(p.stem.split('_'))
    html += f'<tr>\n'\
            f'    <td>{dtg}</td>\n'\
            f'    <td><a href="{p.as_posix()}">{name.title()}</a></td>\n'\
            f'</tr>\n'

html += """</table>
</body>
</html>
"""

with open('index.html', 'w') as f:
    f.write(html)
