#!/Users/ruslanaskarov/.virtualenvs/sigma-cyber-shield-desktop/bin/python

import re
import os
import sys
import logging
import traceback
import hashlib
import json
from urllib.parse import urlparse
import urllib3
import warnings

import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import mysql.connector


urllib3.disable_warnings()
warnings.filterwarnings("ignore")

PATH = os.path.dirname(os.path.abspath(__file__))


logger = logging.getLogger('cyber_shield_app')
logger.setLevel(logging.INFO)
fh = logging.FileHandler('{}/cyber_shield.log'.format(PATH))
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
fh.setFormatter(formatter)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

os.environ['NO_PROXY'] = '*'

REWRITE_URL = 'http://127.0.0.1:8000/block.html'
STOP_URL = 'http://127.0.0.1:8000/stop.html'
API_URL = 'https://odc24.rbc-group.uz/api'

NOTIFICATION_TEMPLATE = '''
osascript -e 'display notification "{}" with title "{}" sound name "Glass"'
'''

_BLOCK_CONTENT = {
    'Payme': {
        'level': 'critical',
        'title': 'Стоп мошенник',
        'message': 'Доступ к контенту ограничен. Так как содержит опасный контент!',
        'block': True,
        'domain': 'payme.uz'
    },
    'sexX': {
        'level': 'critical',
        'title': 'Стоп мошенник',
        'message': 'Доступ к контенту ограничен. Контент сексуального характера!',
        'block': True,
    },
}
_BLOCK_URL = {
    'yandex.ru': {
        'level': 'info',
        'title': 'Предупреждение',
        'message': 'Будьте аккуратны, сайт содержит недостоверный материал',
        'block': False,
    },
    'https://habr.com/ru/articles/548110/': {
        'level': 'critical',
        'title': 'Опасно',
        'message': 'Сайт был заблокирован. Так как содержит опасный контент!',
        'block': True,
    },
}

MEDIA_TYPES = [
    'swf', 'ogg', 'ogv', 'svg', 'svgz', 'eot', 'otf', 'woff', 'mp4', 'ttf', 'css', 'rss', 'atom', 'js', 'jpg', 'jpeg',
    'gif', 'png', 'ico', 'zip', 'tgz', 'gz', 'rar', 'bz2', 'doc', 'xls', 'exe', 'ppt', 'tar', 'mid', 'midi', 'wav',
    'bmp', 'rtf'
]


def get_hosts():
    r = requests.get('https://odc24.rbc-group.uz/api/hosts/', timeout=3)
    if r.status_code == 200:
        text = r.content.decode('utf-8', 'ignore').strip()
        logger.info('Hosts loaded ...')
    else:
        text = open('{}/hosts.json'.format(PATH)).read().strip()
    h = [d['url'] for d in json.loads(text.replace('|', ''))]
    return '|'.join(h)


def get_keywords():
    content = {}
    r = requests.get('https://odc24.rbc-group.uz/api/keywords/', timeout=3)
    if r.status_code == 200:
        text = r.content.decode('utf-8', 'ignore').strip()
        logger.info('Keywords loaded ...')
    else:
        text = open('keywords.json').read()
    for d in json.loads(text):
        w = d['keyword']
        content[w] = {
            'level': 'critical',
            'title': 'Стоп мошенник',
            'message': 'Доступ к контенту ограничен. Контент сексуального характера!',
            'block': True,
            'domain': d['allowed_for_host'],
        }
    return content


RE = re.compile(get_hosts())
BLOCK_CONTENT = get_keywords()


def is_media(url):
    return any(map(lambda x: '.' + x in url, MEDIA_TYPES))


def get_page(url):
    try:
        if not url.startswith('http'):
            return ''

        if is_media(url):
            return ''

        h = requests.head(url, allow_redirects=True, verify=False, timeout=3)
        # only HTML pages
        ct = h.headers['Content-Type']
        if not ct.startswith('text/html') and not ct.startswith('application/json'):
            return ''

        logger.info('>>> {}'.format(url))
        c = requests.get(url, verify=False, timeout=3)
        if c.status_code != 200:
            return ''
        return c.content.decode('utf-8', 'ignore').strip()
    except:
        traceback.print_exc()
        return ''


def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    texts = soup.findAll(text=True)
    visible_texts = filter(tag_visible, texts)
    return u" ".join(t.strip() for t in visible_texts)


def md5(value):
    return hashlib.md5(value.encode()).hexdigest()


def get_clickhouse_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        user='default',
        password='',
        port=9004,
        database='default',
        charset='utf8mb4',
    )


def get_sphinx_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='',
        database='',
        charset='utf8mb4',
        autocommit=True,
    )


def write_content(url, content):
    if content and content is not None and content.strip():
        filename = '{}/history/{}.html'.format(PATH, md5(url))
        # Write to history file
        if content is not None and content.strip():
            open(filename, 'w').write("{}\n{}".format(url, content))

        # todo: Send to AI

        # CLICKHOUSE FOR ANALYTICS
        # connection = get_clickhouse_connection()
        # cursor = connection.cursor()
        # cursor.execute("""INSERT INTO cs_history (url, data) VALUES ('{}', '{}');""".format(url, content))

        # Sphinx
        # connection = get_sphinx_connection()
        # cursor = connection.cursor()
        # cursor.execute("""INSERT INTO fts_cs (url, data) VALUES ('{}', '{}');""".format(url, content))


def notify(title, message):
    os.system(
        NOTIFICATION_TEMPLATE.strip().format(message, title)
    )


def main():
    request = sys.stdin.readline()
    while request:
        [ch_id, url, ip_addr, http_method, user_login] = request.split()

        parse = urlparse(url)

        response = ch_id + ' OK'

        if not is_media(url) and parse.netloc and http_method == 'GET':
            logger.info(request)

            content = get_page(url)

            if content:
                visible_content = text_from_html(content).lower()
                write_content(url, visible_content)

                find_urls = RE.findall(url)

                # find_words = any(map(lambda x: x in content, BLOCK_CONTENT.keys()))
                # find_words = any(map(lambda x: x in content, BLOCK_CONTENT.keys()))
                find_words = [w for w in BLOCK_CONTENT.keys() if w in visible_content]
                if find_urls or find_words:
                    if find_words:
                        data = BLOCK_CONTENT.get(find_words[0])
                        domain = data.get('domain')
                        if domain and parse.netloc == domain:
                            # ignore site
                            pass
                        else:
                            if data.get('block'):
                                response += ' status=301 url={}'.format(STOP_URL)
                            notify(data.get('title'), data.get('message'))
                            logger.info('[Block by Word] {}'.format(find_words[0]))
                    elif find_urls:
                        #data = BLOCK_URL.get(find_urls[0])
                        #if data.get('block'):
                        #    response += ' status=301 url={}'.format(REWRITE_URL)
                        logger.info('[Block by URL] {}'.format(url))
                        response += ' status=301 url={}'.format(REWRITE_URL)
                        notify('Опасный сайт', 'Сайт был заблокирован. Так как содержит опасный контент!')

        response += '\n'
        sys.stdout.write(response)
        sys.stdout.flush()
        request = sys.stdin.readline()


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        logging.error(traceback.format_exc())
        # print(ex.__str__())
