import scrapy
import re
from urllib.parse import urlparse, urlencode, parse_qs
# 3 импорт исправлен на абсолютный
from dentomir_parser.items import DentomirProductItem

class DentomirSpider(scrapy.Spider):
    name = 'dentomir'
    allowed_domains = ['dentomirshop.ru']
    start_urls = ['https://dentomirshop.ru/catalog/']
    def __init__(self, *args, **kwargs):
        super(DentomirSpider, self).__init__(*args, **kwargs)
        self.logger.info("Запуск в полном режиме. Будут собраны все товары.")

    def parse(self, response):
        self.logger.info(f"Сбор категорий с главной страницы каталога: {response.url}")
        
        category_links = response.xpath('//div[contains(@class, "sections-block__wrapper")]/div/a')
        
        if not category_links:
            self.logger.error("Не удалось найти ссылки на категории! Проверьте XPath-селектор.")

        for link in category_links:
            href = link.xpath('./@href').get()
            if href:
                yield response.follow(href, callback=self.parse_category)

    # 4 пагинация сначала находим число страниц, потом генерируем все запросы
    def parse_category(self, response):
        self.logger.info(f"Анализ пагинации для категории: {response.url.split('?')[0]}")
        page_links_text = response.xpath('//div[contains(@class, "module-pagination__wrapper")]//a/text()').getall()
        page_numbers = [int(num) for num in page_links_text if num.strip().isdigit()]
        total_pages = max(page_numbers) if page_numbers else 1
        self.logger.info(f"Найдено {total_pages} страниц. Генерация запросов...")

        # генерируем запросы на все страницы от 1 до последней
        for page_num in range(1, total_pages + 1):
            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)
            query_params['PAGEN_1'] = [str(page_num)]

            # для страниц > 1 добавляем AJAX-параметры
            if page_num > 1:
                query_params['AJAX_REQUEST'] = ['Y']
                query_params['ajax_get'] = ['Y']
                query_params['bitrix_include_areas'] = ['N']
            
            page_url = parsed_url._replace(query=urlencode(query_params, doseq=True)).geturl()
            

            yield scrapy.Request(page_url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        self.logger.info(f"Сбор товаров со страницы: {response.url}")
        
        product_links = response.xpath('//div[contains(@class, "catalog-block__info-title")]/a/@href').getall()
        for href in product_links:
            yield response.follow(href, callback=self.parse_product)
            
    def parse_product(self, response):
        self.logger.info(f"Парсинг товара: {response.url}")
        
        item = DentomirProductItem()
        item['url'] = response.url
        
        # 5 категории собирать массивом убирать первые 2 элемента
        breadcrumbs_raw = response.xpath('//div[@id="navigation"]//span[@itemprop="name"]/text()').getall()
        item['category'] = [b.strip() for b in breadcrumbs_raw[2:-1] if b.strip()]

        item['name'] = response.xpath('//h1/text()').get('').strip() or None
        item['sku'] = response.xpath('//div[contains(@class, "article__value")]/text()').get('').strip() or None

        description_parts = response.xpath('//div[@id="desc"]//text()').getall()
        item['description'] = '\n'.join([part.strip() for part in description_parts if part.strip()]) or None

        # 6 цены привести к числовому значению
        price_str = response.xpath('string(//div[contains(@class, "price--actual")]//span[contains(@class, "price_value")])').get() or \
                    response.xpath('string(//div[contains(@class, "price__new")]/span[contains(@class, "price__new-val")])').get()
        
        price_numeric = None
        if price_str:
            clean_price = re.sub(r'[^0-9.]', '', price_str)
            try: price_numeric = float(clean_price)
            except (ValueError, TypeError): pass

        item['price_regular'] = price_numeric
        item['price_discounted'] = price_numeric

        brand_raw = response.xpath('//div[contains(@class, "brand")]//a/img/@title').get() or \
                    response.xpath('//div[contains(@class, "brand-detail-info__title")]//a/text()').get()
        item['brand'] = brand_raw.strip() if brand_raw else None

        # 7 наличие должно быть вида true-/false
        availability_raw = response.xpath('//span[contains(@class, "status-container") and contains(@class, "instock")]//span[contains(@class, "js-replace-status")]/text()').get() or \
                           response.xpath('//div[contains(@class, "item-stock")]//span[contains(@class, "store_view")]/text()').get()
        item['availability'] = bool(availability_raw and 'наличии' in availability_raw.lower())

        # 8 рейтинг не может быть нулевым
        rating_str = response.xpath('//div[contains(@class, "rating")]//*[contains(@class, "rating__value")]/text()').get('').strip()
        rating_val = None
        if rating_str:
            try:
                rating_float = float(rating_str)
                if rating_float > 0: rating_val = rating_float
            except (ValueError, TypeError): pass
        item['rating'] = rating_val

        # 9 review_count не может быть none если нет - 0
        review_text = response.xpath('//div[contains(@class, "rating")]//a[contains(@class, "rating-link")]/text()').get() or \
                      response.xpath('//div[contains(@class, "rating")]//*[contains(@class, "rating__count")]/span/text()').get('')
        review_count_match = re.search(r'\d+', review_text)
        item['review_count'] = int(review_count_match.group(0)) if review_count_match else 0

        image_hrefs = response.xpath('//div[contains(@class, "detail-gallery-big__item")]/a/@href').getall()
        item['image_urls'] = [response.urljoin(href) for href in image_hrefs] if image_hrefs else None
        
        yield item