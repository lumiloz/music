# Genera voz neural (edge-tts) para cada pedido en voz/pedidos/*.json que no tenga salida.
# Pedido: {"voice": "es-MX-JorgeNeural", "rate": "+8%", "pitch": "+0Hz", "text": "..."}
# Salida: voz/salida/<nombre>.mp3 y <nombre>.json (palabras con offset/duración en segundos)
import asyncio, json, glob, os, edge_tts
os.makedirs('voz/salida', exist_ok=True)
async def run(p):
    name = os.path.splitext(os.path.basename(p))[0]
    if os.path.exists(f'voz/salida/{name}.mp3'): return
    cfg = json.load(open(p, encoding='utf-8'))
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
async def main():
    for p in sorted(glob.glob('voz/pedidos/*.json')): await run(p)
asyncio.run(main())
