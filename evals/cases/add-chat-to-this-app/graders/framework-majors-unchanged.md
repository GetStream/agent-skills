---
type: script
---
python3 -c "import json;d=json.load(open('package.json'))['dependencies'];assert d['next'].lstrip('^~').startswith('16'),d['next'];assert d['react'].lstrip('^~').startswith('19'),d['react'];print('next',d['next'],'react',d['react'])"
