"""Produce a self-contained HTML review artifact, without network assets."""
from pathlib import Path
import re
import sys
root=Path(__file__).resolve().parent
html=(root/'index.html').read_text()
css=(root/'styles.css').read_text()
html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+css+'</style>')
for name in ['data.js','model.js','app.js']:
    code=(root/name).read_text().replace('</script','<\\/script')
    html=html.replace(f'<script src="{name}"></script>','<script>'+code+'</script>')
# One self-contained file. Source links are user-clicked only; no external fonts, scripts or styles.
assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="[^#]',html)
target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(html)
print(f'{target}: {target.stat().st_size} bytes')
