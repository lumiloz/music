# Genera voz neural (edge-tts) para cada pedido en voz/pedidos/*.json que no tenga salida.
# Pedido: {"voice": "es-MX-JorgeNeural", "rate": "+8%", "pitch": "+0Hz", "text": "..."}
# Salida: voz/salida/<nombre>.mp3 y <nombre>.json (palabras con offset/duración en segundos)
# Si falla, deja voz/salida/<nombre>.err con el error (para diagnóstico) y sigue con los demás.
import asyncio, json, glob, os, importlib, traceback, edge_tts, edge_tts.communicate as _ec
def set_fmt(fmt):   # pide mayor calidad al servicio si el pedido lo indica
    p = _ec.__file__; src = open(p).read()
    import re
    src2 = re.sub(r'audio-24khz-\d+kbitrate-mono-mp3', fmt, src)
    if src2 != src: open(p, 'w').write(src2); importlib.reload(_ec); importlib.reload(edge_tts)
os.makedirs('voz/salida', exist_ok=True)
async def synth(name, cfg):
    c = edge_tts.Communicate(cfg['text'], cfg.get('voice', 'es-MX-JorgeNeural'), rate=cfg.get('rate', '+0%'),
                             pitch=cfg.get('pitch', '+0Hz'), volume=cfg.get('volume', '+0%'), boundary='WordBoundary')
    words = []
    with open(f'voz/salida/{name}.mp3', 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                words.append({'w': ch['text'], 't': ch['offset'] / 1e7, 'd': ch['duration'] / 1e7})
    json.dump({'words': words, 'cfg': cfg}, open(f'voz/salida/{name}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('ok', name, len(words))
async def run(p):
    name = os.path.splitext(os.path.basename(p))[0]
    if os.path.exists(f'voz/salida/{name}.mp3') or os.path.exists(f'voz/salida/{name}.err'): return
    try:
        cfg = json.load(open(p, encoding='utf-8'))
        if cfg.get('fmt'): set_fmt(cfg['fmt'])
    except Exception:
        open(f'voz/salida/{name}.err', 'w').write(traceback.format_exc()); return
    err = ''
    for i in range(3):
        try:
            await synth(name, cfg); return
        except Exception:
            err += f'--- intento {i + 1} (edge-tts {getattr(edge_tts, "__version__", "?")})\n' + traceback.format_exc()
            for ext in ('mp3', 'json'):
                if os.path.exists(f'voz/salida/{name}.{ext}'): os.remove(f'voz/salida/{name}.{ext}')
            await asyncio.sleep(3)
    open(f'voz/salida/{name}.err', 'w').write(err); print('ERROR', name)
async def main():
    for p in sorted(glob.glob('voz/pedidos/*.json')): await run(p)
asyncio.run(main())
