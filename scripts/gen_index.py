from pathlib import Path

html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>COVID-19 Analysis</title>
</head>
<body>
<ul>
"""
for p in Path('charts').glob('*.html'):
    name = ' '.join(p.stem.split('_'))
    html += f"""    <li><a href="{p.as_posix()}">{name.title()}</a></li>\n"""

html += """</ul>
</body>
</html>
"""

with open('index.html', 'w') as f:
    f.write(html)
