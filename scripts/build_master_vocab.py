#!/usr/bin/env python3
"""将三个 GitHub 来源的雅思词库合并转换为 ielts-buddy 格式的大词库

来源：
1. fanhongtao/IELTS — 雅思词汇词根+联想记忆法（3700+ 行）
2. hefengxian/ielts-vocabulary — 雅思真经词汇表（2100+ 行，按主题分类）
3. sxwang1991/ielts-word-list — YAML 格式（49 个 word list）

输出：src/ielts_buddy/data/vocab_master.json — 去重合并后的大词库
"""

import json
import re
import os
import sys

def parse_fht(filepath):
    """解析 fanhongtao/IELTS 格式"""
    words = []
    current_list = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('Word List'):
                m = re.search(r'Word List\s+(\d+)', line)
                if m:
                    current_list = int(m.group(1))
                continue
            if line.startswith('README') or line.startswith('《') or line.startswith('以') or line.startswith('根据') or line.startswith('范洪滔') or line.startswith('记录') or line.startswith('本人') or line.startswith('201'):
                continue
            if line.startswith('雅思词汇'):
                continue
            
            # 格式: word   /phonetic/  pos. definition
            m = re.match(r'^(\S+?)[\*]?\s+([/\[\{].+?[/\]\}])\s+(.+)$', line)
            if m:
                word = m.group(1).strip().lower()
                phonetic = m.group(2).strip()
                rest = m.group(3).strip()
                
                # 拆分 pos 和 definition
                pos_match = re.match(r'^([a-z]+\.(?:/[a-z]+\.)*)\s*(.*)$', rest)
                if pos_match:
                    pos = pos_match.group(1)
                    definition = pos_match.group(2)
                else:
                    pos = ''
                    definition = rest
                
                # 标准化 phonetic
                phonetic = phonetic.replace('[', '/').replace(']', '/').replace('{', '/').replace('}', '/')
                
                words.append({
                    'word': word,
                    'phonetic': phonetic,
                    'pos': pos,
                    'definition': definition,
                    'source': 'fht',
                    'list_num': current_list
                })
    
    return words


def parse_hfx(filepath):
    """解析 hefengxian/ielts-vocabulary 格式"""
    words = []
    current_topic = 'general'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line == '---' or line == '+++':
                continue
            
            # 主题行（纯中文，没有 |）
            if '|' not in line and re.match(r'^[\u4e00-\u9fff]+', line):
                current_topic = line
                continue
            
            parts = line.split('|')
            if len(parts) >= 3:
                word = parts[0].strip().lower()
                pos = parts[1].strip()
                definition = parts[2].strip()
                example = parts[3].strip() if len(parts) > 3 else ''
                # 有些有额外注释在 parts[4]
                
                words.append({
                    'word': word,
                    'phonetic': '',
                    'pos': pos,
                    'definition': definition,
                    'example_en': example,
                    'topic_zh': current_topic,
                    'source': 'hfx'
                })
    
    return words


def parse_sxw_yaml(filepath):
    """解析 sxwang1991/ielts-word-list YAML 格式"""
    words = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 简单 YAML 解析（不用 pyyaml 避免依赖）
    # 每个词条格式: 
    # word:
    #   title: word
    #   text: __word__ [phonetic] pos. definition
    #   example: ...
    
    entries = re.split(r'\n(?=\w[\w\s-]*:\s*$)', content, flags=re.MULTILINE)
    
    for entry in entries:
        lines = entry.strip().split('\n')
        if not lines:
            continue
        
        # 跳过注释和空白
        if lines[0].startswith('#') or lines[0].startswith('=='):
            continue
        
        word_name = ''
        phonetic = ''
        pos = ''
        definition = ''
        example = ''
        
        for line in lines:
            line = line.strip()
            if line.startswith('title:'):
                word_name = line.split(':', 1)[1].strip().lower()
            elif line.startswith('text:') or (line.startswith('__') and '__' in line[2:]):
                text = line.split(':', 1)[1].strip() if ':' in line else line
                text = text.strip('|').strip()
                # 解析 __word__ [phonetic] pos. definition
                m = re.match(r'__(\S+?)__\s*([/\[\(].+?[/\]\)])\s*(.+)', text)
                if m:
                    if not word_name:
                        word_name = m.group(1).lower()
                    phonetic = m.group(2).replace('[', '/').replace(']', '/')
                    rest = m.group(3).strip()
                    pos_match = re.match(r'^([a-z]+\.(?:/[a-z]+\.)*)\s*(.*)$', rest)
                    if pos_match:
                        pos = pos_match.group(1)
                        definition = pos_match.group(2)
                    else:
                        definition = rest
            elif line.startswith('example:'):
                example = line.split(':', 1)[1].strip()
        
        if word_name and (definition or phonetic):
            words.append({
                'word': word_name,
                'phonetic': phonetic,
                'pos': pos,
                'definition': definition,
                'example_en': example,
                'source': 'sxw'
            })
    
    return words


# 主题映射：中文主题 → 英文
TOPIC_MAP = {
    '自然地理': 'science', '物理': 'science', '化学': 'science', '天文': 'science',
    '生物': 'science', '数学': 'science', '医学': 'health', '心理': 'health',
    '教育': 'education', '学习': 'education', '学术': 'education', '考试': 'education',
    '经济': 'economy', '商业': 'economy', '金融': 'economy', '贸易': 'economy',
    '科技': 'technology', '计算机': 'technology', '互联网': 'technology', '通信': 'technology',
    '社会': 'society', '法律': 'society', '政治': 'society', '政府': 'society',
    '犯罪': 'crime', '文化': 'culture', '艺术': 'culture', '文学': 'culture',
    '历史': 'culture', '宗教': 'culture', '建筑': 'culture',
    '环境': 'environment', '气候': 'environment', '生态': 'environment', '能源': 'environment',
    '健康': 'health', '运动': 'health', '食物': 'health', '饮食': 'health',
    '媒体': 'media', '新闻': 'media', '旅游': 'travel', '交通': 'travel',
}

def map_topic(topic_zh):
    """将中文主题映射到英文"""
    for key, value in TOPIC_MAP.items():
        if key in (topic_zh or ''):
            return value
    return 'general'


def estimate_band(word, list_num=0, source=''):
    """根据词频/来源估算 Band 级别"""
    common_words = {'the','is','are','was','were','be','been','have','has','had',
                    'do','does','did','say','get','make','go','know','take','see',
                    'come','think','look','want','give','use','find','tell'}
    if word.lower() in common_words:
        return 5
    
    word_len = len(word)
    
    if source == 'fht':
        # fanhongtao 按 Word List 排序，越靠后越难
        if list_num <= 12:
            return 5
        elif list_num <= 24:
            return 6
        elif list_num <= 36:
            return 7
        elif list_num <= 44:
            return 8
        else:
            return 9
    elif source == 'hfx':
        # 按词长和词性粗估
        if word_len <= 5:
            return 5
        elif word_len <= 7:
            return 6
        elif word_len <= 9:
            return 7
        else:
            return 8
    else:
        if word_len <= 6:
            return 6
        elif word_len <= 8:
            return 7
        else:
            return 8
    return 7


def merge_and_dedupe(fht_words, hfx_words, sxw_words):
    """合并去重，保留最丰富的信息"""
    word_map = {}  # word -> best entry
    
    all_words = fht_words + hfx_words + sxw_words
    
    for w in all_words:
        key = w['word'].lower().strip()
        if not key or len(key) < 2:
            continue
        # 跳过非英文
        if not re.match(r'^[a-z]', key):
            continue
        
        if key not in word_map:
            word_map[key] = {
                'word': key,
                'phonetic': w.get('phonetic', ''),
                'pos': w.get('pos', ''),
                'definition': w.get('definition', ''),
                'example': {'en': w.get('example_en', ''), 'zh': ''},
                'collocations': [],
                'synonyms': [],
                'etymology': '',
                'topic': map_topic(w.get('topic_zh', '')),
                'band': estimate_band(key, w.get('list_num', 0), w.get('source', '')),
            }
        else:
            existing = word_map[key]
            # 合并信息：取更丰富的
            if not existing['phonetic'] and w.get('phonetic'):
                existing['phonetic'] = w['phonetic']
            if not existing['pos'] and w.get('pos'):
                existing['pos'] = w['pos']
            if not existing['definition'] and w.get('definition'):
                existing['definition'] = w['definition']
            elif w.get('definition') and len(w['definition']) > len(existing['definition']):
                existing['definition'] = w['definition']
            if not existing['example']['en'] and w.get('example_en'):
                existing['example']['en'] = w['example_en']
            if w.get('topic_zh') and existing['topic'] == 'general':
                existing['topic'] = map_topic(w['topic_zh'])
    
    return list(word_map.values())


def main():
    src_dir = '/tmp/ielts-sources'
    
    print('解析 fanhongtao/IELTS...')
    fht = parse_fht(f'{src_dir}/fht.txt')
    print(f'  → {len(fht)} 词')
    
    print('解析 hefengxian/ielts-vocabulary...')
    hfx = parse_hfx(f'{src_dir}/hfx.txt')
    print(f'  → {len(hfx)} 词')
    
    print('解析 sxwang1991/ielts-word-list...')
    sxw = parse_sxw_yaml(f'{src_dir}/sxw.yaml')
    print(f'  → {len(sxw)} 词')
    
    print('合并去重...')
    merged = merge_and_dedupe(fht, hfx, sxw)
    print(f'  → {len(merged)} 个不重复单词')
    
    # 统计
    band_count = {}
    topic_count = {}
    for w in merged:
        b = w['band']
        t = w['topic']
        band_count[b] = band_count.get(b, 0) + 1
        topic_count[t] = topic_count.get(t, 0) + 1
    
    print('\nBand 分布:')
    for b in sorted(band_count):
        print(f'  Band {b}: {band_count[b]}')
    
    print('\n主题分布:')
    for t in sorted(topic_count, key=lambda x: topic_count[x], reverse=True)[:15]:
        print(f'  {t}: {topic_count[t]}')
    
    # 输出
    out_path = '/home/node/clawd/projects/ielts-buddy/src/ielts_buddy/data/vocab_master.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f'\n✅ 输出: {out_path}')
    print(f'   {len(merged)} 词, {size_mb:.1f} MB')


if __name__ == '__main__':
    main()
