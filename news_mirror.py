# -*- coding: utf-8 -*-
"""J11 GNN 新聞鏡像：爬 GNN 巴哈姆特 ACG 新聞 -> news-cache.json"""
import re, json, io, os, sys, time
import urllib.request

URL = 'https://gnn.gamer.com.tw/?k=5&t=4'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'news-cache.json')

def fetch(url, timeout=25, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'replace')
        except Exception as e:
            last = e
            time.sleep(3)
    raise last

def clean_date(raw):
    raw = re.sub(r'<span[^>]*>.*?</span>', '', raw, flags=re.S)
    return re.sub(r'<[^>]+>', '', raw).strip()

def parse(html):
    # date headers: <p class="GN-lbox2A" ...>10 月 16 日<span ...>...</span></p>
    dates = re.findall(r'<p class="GN-lbox2A"[^>]*>(.*?)</p>', html, re.S)
    date_labels = [clean_date(d) for d in dates]
    # news blocks
    blocks = re.split(r'<div class="GN-lbox2B">', html)[1:]
    articles = []
    prev_date = date_labels[0] if date_labels else ''
    for b in blocks:
        # if block starts with a date marker, update date
        m_date = re.match(r'\s*<p class="GN-lbox2A"[^>]*>(.*?)</p>', b, re.S)
        if m_date:
            prev_date = clean_date(m_date.group(1))
        # skip pure date blocks (no news content)
        if 'detail.php?sn=' not in b:
            continue
        m_link = re.search(r'<a href="(//gnn\.gamer\.com\.tw/detail\.php\?sn=(\d+))"[^>]*>([^<]+)</a>', b)
        if not m_link:
            continue
        url_rel, sn, title = m_link.group(1), m_link.group(2), m_link.group(3).strip()
        m_img = re.search(r'<img src="([^"]+)"', b)
        m_plat = re.search(r'platform-tag_list platform-\w+">([^<]+)</div>', b)
        m_sum = re.search(r'<p class="GN-lbox2C">(.*?)<a href=', b, re.S)
        m_push = re.search(r'(\d+)\s*人推', b)
        summary = ''
        if m_sum:
            summary = re.sub(r'<[^>]+>', '', m_sum.group(1)).strip()
            summary = summary.replace('&nbsp;', ' ').replace('&Eacute;', 'É').strip()
        articles.append({
            'id': sn,
            'title': title,
            'url': 'https://gnn.gamer.com.tw/detail.php?sn=%s' % sn,
            'img': m_img.group(1) if m_img else '',
            'platform': m_plat.group(1).strip() if m_plat else '',
            'date': prev_date,
            'summary': summary[:160],
            'push': int(m_push.group(1)) if m_push else 0
        })
    return articles

def main():
    html = fetch(URL)
    arts = parse(html)
    now = time.strftime('%Y-%m-%d %H:%M')
    payload = {'fetched_at': now, 'source': URL, 'articles': arts}
    with io.open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print('articles:', len(arts), 'fetched_at:', now)

if __name__ == '__main__':
    main()
