import os, re
p = '/home/oanh/cccccccccccccc/ecostream/cli.py'
if os.path.exists(p):
    with open(p, 'r', encoding='utf-8') as f: c = f.read()
    c = c.replace('total_co2e_tonnes', 'total_co2e_tonnes')
    # Let's not modify CLI deeply right now
