# Genera voz neural para cada pedido en voz/pedidos/*.json que no tenga salida.
# Pedido edge: {"voice": "es-MX-JorgeNeural", "rate": "+5%", "text": "..."} -> <nombre>.mp3 + <nombre>.json (palabras)
# Pedido bing: {"engine": "bing", "voice": "es-MX-JorgeNeural", "rate": "+5%", "lines": ["...", "..."]}
#              -> <nombre>_00.mp3, <nombre>_01.mp3 ... + <nombre>.json (lista de archivos)
# Si falla, deja voz/salida/<nombre>.err con el error y sigue con los demás.
import asyncio, json, glob, os, importlib, traceback, re, time, urllib.request, urllib.parse, http.cookiejar
from xml.sax.saxutils import escape
os.makedirs('voz/salida', exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0'
def bing_session():
    cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [('User-Agent', UA), ('Accept-Language', 'es-MX,es;q=0.9')]
    html = op.open('https://www.bing.com/translator', timeout=30).read().decode('utf-8', 'ignore')
    ig = re.search(r'IG:"([^"]+)"', html).group(1)
    iid = re.search(r'data-iid="([^"]+)"', html).group(1)
    key, token = re.search(r'params_AbusePreventionHelper\s*=\s*\[(\d+),"([^"]+)"', html).groups()
    return op, ig, iid, key, token
def bing_tts(sess, text, voice, rate, n):
    op, ig, iid, key, token = sess
    lang = '-'.join(voice.split('-')[:2])
    ssml = (f"<speak version='1.0' xml:lang='{lang}'><voice xml:lang='{lang}' name='{voice}'>"
            f"<prosody rate='{rate}'>{escape(text)}</prosody></voice></speak>")
    data = urllib.parse.urlencode({'ssml': ssml, 'token': token, 'key': key}).encode()
    url = f'https://www.bing.com/tfettts?isVertical=1&&IG={ig}&IID={iid}.{n}'
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded',
                                                          'Origin': 'https://www.bing.com', 'Referer': 'https://www.bing.com/translator'})
    r = op.open(req, timeout=60); b = r.read()
    if len(b) < 2000 or b[:1] == b'{' or b[:1] == b'<': raise RuntimeError(f'respuesta inesperada {r.status} {b[:300]!r}')
    return b
def run_bing(name, cfg):
    sess = bing_session(); out = []
    for i, line in enumerate(cfg['lines']):
        for k in range(3):
            try:
                b = bing_tts(sess, line, cfg.get('voice', 'es-MX-JorgeNeural'), cfg.get('rate', '+0%'), i + 2); break
            except Exception:
                if k == 2: raise
                time.sleep(4); sess = bing_session()
        fn = f'{name}_{i:02d}.mp3'; open(f'voz/salida/{fn}', 'wb').write(b); out.append(fn); time.sleep(1.5)
    json.dump({'files': out, 'cfg': cfg}, open(f'voz/salida/{name}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('ok bing', name, len(out))
async def run_edge(name, cfg):
    import edge_tts
    c = edge_tts.Communicate(cfg['text'], cfg.get('voice', 'es-MX-JorgeNeural'), rate=cfg.get('rate', '+0%'),
                             pitch=cfg.get('pitch', '+0Hz'), volume=cfg.get('volume', '+0%'), boundary='WordBoundary')
    words = []
    with open(f'voz/salida/{name}.mp3', 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                words.append({'w': ch['text'], 't': ch['offset'] / 1e7, 'd': ch['duration'] / 1e7})
    json.dump({'words': words, 'cfg': cfg}, open(f'voz/salida/{name}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('ok edge', name, len(words))
async def run(p):
    name = os.path.splitext(os.path.basename(p))[0]
    if any(os.path.exists(f'voz/salida/{name}.{e}') for e in ('json', 'mp3', 'err')): return
    try:
        cfg = json.load(open(p, encoding='utf-8'))
        if cfg.get('engine') == 'bing': run_bing(name, cfg)
        else: await run_edge(name, cfg)
    except Exception:
        for f in glob.glob(f'voz/salida/{name}.mp3') + glob.glob(f'voz/salida/{name}.json'): os.remove(f)
        open(f'voz/salida/{name}.err', 'w').write(traceback.format_exc()); print('ERROR', name)
async def main():
    for p in sorted(glob.glob('voz/pedidos/*.json')): await run(p)
asyncio.run(main())
