import sys
import os
import re
import math
import json
import base64
import argparse
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw, ImageFilter

EVO_URL = os.environ.get('EVO_URL', 'http://localhost:9001')
EVO_KEY = os.environ.get('EVO_KEY', 'rahasia_okta_123')
EVO_INSTANCE = os.environ.get('EVO_INSTANCE', 'okta_wa')

def send_evolution_media(number, b64_str, caption, filename='image.jpg'):
    url = f"{EVO_URL}/message/sendMedia/{EVO_INSTANCE}"
    payload = {
        'number': number,
        'mediatype': 'image',
        'mimetype': 'image/jpeg',
        'caption': caption,
        'media': b64_str,
        'fileName': filename
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'apikey': EVO_KEY}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, resp.read().decode('utf-8')

def send_evolution_text(number, text):
    url = f"{EVO_URL}/message/sendText/{EVO_INSTANCE}"
    payload = {'number': number, 'text': text}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'apikey': EVO_KEY}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode('utf-8')

def render_math_curve(output_path):
    W, H = 1920, 720
    bg = Image.new('RGBA', (W, H), (8, 10, 20, 255))

    def to_screen(x, y):
        sx = int((x - (-17.5)) / 30.0 * (W - 200) + 100)
        sy = int((1.0 - (y - (-2.5)) / 5.0) * (H - 200) + 100)
        return (sx, sy)

    grid_draw = ImageDraw.Draw(bg)
    for gx in range(-16, 13, 2):
        grid_draw.line([to_screen(gx, -2.5), to_screen(gx, 2.5)], fill=(22, 28, 52, 255), width=1)
    for gy in [-2, -1, 0, 1, 2]:
        grid_draw.line([to_screen(-17.5, gy), to_screen(12.5, gy)], fill=(22, 28, 52, 255), width=1)
    grid_draw.line([to_screen(-17.5, 0), to_screen(12.5, 0)], fill=(35, 45, 80, 255), width=2)

    heart_pts = []
    for i in range(1001):
        t = 2.0 * math.pi * i / 1000.0
        x = -14.0 + 1.92 * (math.sin(t) ** 3)
        y = 0.12 * (13.0 * math.cos(t) - 5.0 * math.cos(2*t) - 2.0 * math.cos(3*t) - math.cos(4*t))
        heart_pts.append(to_screen(x, y))

    polylines = [
        [(-10.8, 1.5), (-10.8, -0.8), (-10.5, -1.4), (-9.8, -1.6), (-9.1, -1.4), (-8.8, -0.8), (-8.8, 1.5)],
        [(-6.9, -1.5), (-6.9, 1.5), (-5.5, -0.1), (-4.1, 1.5), (-4.1, -1.5)],
        [(-3.0, -1.5), (-1.7, 1.5), (-0.4, -1.5)],
        [(0.6, -1.5), (0.6, 1.5), (3.2, -1.5), (3.2, 1.5)],
        [(4.3, -1.5), (4.3, 1.5), (5.45, 1.5), (6.5, 0.9), (6.9, 0.1), (6.9, -0.1), (6.5, -0.9), (5.45, -1.5), (4.3, -1.5)],
        [(8.1, -1.5), (9.4, 1.5), (10.7, -1.5)],
    ]
    letter_lines = [[to_screen(x, y) for (x, y) in poly] for poly in polylines]
    segments = [
        [to_screen(-2.5, -0.35), to_screen(-0.9, -0.35)],
        [to_screen(8.6, -0.35), to_screen(10.2, -0.35)]
    ]

    heart_glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(heart_glow)
    h_draw.line(heart_pts, fill=(255, 20, 100, 255), width=24, joint='curve')
    heart_glow = heart_glow.filter(ImageFilter.GaussianBlur(18))

    heart_mid = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    hm_draw = ImageDraw.Draw(heart_mid)
    hm_draw.line(heart_pts, fill=(255, 60, 140, 255), width=12, joint='curve')
    heart_mid = heart_mid.filter(ImageFilter.GaussianBlur(6))

    heart_core = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    hc_draw = ImageDraw.Draw(heart_core)
    hc_draw.line(heart_pts, fill=(255, 255, 255, 255), width=3, joint='curve')

    letter_glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    l_draw = ImageDraw.Draw(letter_glow)
    for line in letter_lines:
        l_draw.line(line, fill=(0, 180, 255, 255), width=24, joint='curve')
    for seg in segments:
        l_draw.line(seg, fill=(0, 180, 255, 255), width=24, joint='curve')
    letter_glow = letter_glow.filter(ImageFilter.GaussianBlur(18))

    letter_mid = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lm_draw = ImageDraw.Draw(letter_mid)
    for line in letter_lines:
        lm_draw.line(line, fill=(0, 230, 255, 255), width=12, joint='curve')
    for seg in segments:
        lm_draw.line(seg, fill=(0, 230, 255, 255), width=12, joint='curve')
    letter_mid = letter_mid.filter(ImageFilter.GaussianBlur(6))

    letter_core = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lc_draw = ImageDraw.Draw(letter_core)
    for line in letter_lines:
        lc_draw.line(line, fill=(255, 255, 255, 255), width=3, joint='curve')
    for seg in segments:
        lc_draw.line(seg, fill=(255, 255, 255, 255), width=3, joint='curve')

    final_img = Image.alpha_composite(bg, heart_glow)
    final_img = Image.alpha_composite(final_img, heart_mid)
    final_img = Image.alpha_composite(final_img, heart_core)
    final_img = Image.alpha_composite(final_img, letter_glow)
    final_img = Image.alpha_composite(final_img, letter_mid)
    final_img = Image.alpha_composite(final_img, letter_core)

    tdraw = ImageDraw.Draw(final_img)
    tdraw.text((W // 2, 50), '❤️  U M A N D A  •  M A T H E M A T I C A L   C U R V E', fill=(130, 150, 200, 200), anchor='mm')
    tdraw.text((W // 2, H - 40), 'Curve(-14 + 1.92*sin(t)^3, 0.12*(13*cos(t)-5*cos(2t)-2*cos(3t)-cos(4t))) | Polylines U M A N D A', fill=(70, 85, 125, 200), anchor='mm')

    rgb_img = final_img.convert('RGB')
    rgb_img.save(output_path, quality=95)
    return output_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--number', required=True)
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--caption', default='Hasil Gambar AI')
    parser.add_argument('--raw_text', default='')
    args = parser.parse_args()

    number = args.number
    prompt = args.prompt
    caption = args.caption
    raw_text = args.raw_text

    print(f"Processing image request for {number}...")
    print(f"Prompt: {prompt[:80]}...")

    combined = f"{prompt} {raw_text}"
    is_math = bool(re.search(r'Curve\(|Polyline\(|Segment\(|persamaan|math curve|umanda', combined, re.IGNORECASE))

    if is_math:
        print("Detected mathematical curve request. Rendering pure Pillow neon curve...")
        out_file = '/tmp/math_neon_render.jpg'
        render_math_curve(out_file)
        with open(out_file, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
        
        full_caption = f"✨ *Hasil Visualisasi Persamaan Matematika (❤️ U M A N D A)*\n\n{caption}\n\n_Render: Cyber Neon Glow (Pink & Electric Cyan) 1920x720_"
        status, resp = send_evolution_media(number, b64_data, full_caption, 'math_curve.jpg')
        print(f"Delivered math render: status {status}")
        return

    enc_prompt = urllib.parse.quote(prompt)
    candidate_urls = [
        f"https://image.pollinations.ai/prompt/{enc_prompt}?model=sana&width=768&height=768&nologo=true",
        f"https://image.pollinations.ai/prompt/{enc_prompt}?model=sana&width=512&height=512&nologo=true"
    ]

    img_data = None
    for url in candidate_urls:
        try:
            print(f"Trying URL: {url[:70]}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=18) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if len(data) > 1000 and (data[:2] == b'\xff\xd8' or data[:4] == b'\x89PNG'):
                        img_data = data
                        print(f"Successfully downloaded image: {len(data)} bytes")
                        break
        except Exception as e:
            print(f"Attempt failed: {e}")
            continue

    if img_data:
        b64_str = base64.b64encode(img_data).decode('utf-8')
        full_caption = f"🎨 *Hasil Gambar AI*\n\n{caption}\n\n_Prompt: {prompt}_"
        status, resp = send_evolution_media(number, b64_str, full_caption, 'generated.jpg')
        print(f"Delivered AI image: status {status}")
    else:
        print("Image generation timed out on all attempts.")
        send_evolution_text(
            number,
            f"⚠️ *Generator Gambar AI*: Server pembuat gambar sedang mengalami antrean padat saat memproses prompt: \"_{prompt[:50]}..._\".\n\nSilakan coba kirim ulang dalam beberapa saat ya bro!"
        )

if __name__ == '__main__':
    main()
