import os
from datetime import datetime

BOT_NAME = "dentomir_parser"
SPIDER_MODULES = ["dentomir_parser.spiders"]
NEWSPIDER_MODULE = "dentomir_parser.spiders"
ROBOTSTXT_OBEY = False
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
DOWNLOAD_DELAY = 1
FEEDS = {
    'products.json': {
        'format': 'json',
        'encoding': 'utf8',
        'store_empty': False,
        'indent': 4,
        'overwrite': True
    },
}

LOG_LEVEL = 'INFO'
LOG_FILE = f"./logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
os.makedirs("logs", exist_ok=True)


# тестовый режим сколько собирать
CLOSESPIDER_ITEMCOUNT = 5