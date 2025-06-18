import scrapy
import re
from urllib.parse import urlparse, urlencode, parse_qs
from ..items import DentomirProductItem
from scrapy.exceptions import CloseSpider

class DentomirSpider(scrapy.Spider):
    name = 'dentomir'
    allowed_domains = ['dentomirshop.ru']
    start_urls = ['https://dentomirshop.ru/catalog/']

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(DentomirSpider, cls).from_crawler(crawler, *args, **kwargs)
        spider.item_count = 0
        spider.limit = spider.settings.getint('CLOSESPIDER_ITEMCOUNT', 0)
        
        if spider.limit:
            spider.logger.info(f"ВНИМАНИЕ: Включен тестовый режим. Паук остановится после сбора {spider.limit} товаров.")
        else:
            spider.logger.info("Запуск в полном режиме. Будут собраны все товары.")
            
        return spider

    def parse(self, response):
        self.logger.info(f"Сбор категорий с главной страницы каталога: {response.url}")
        
        category_links = response.xpath('//div[contains(@class, "sections-block__wrapper")]/div/a')
        
        if not category_links:
            self.logger.error("Не удалось найти ссылки на категории! Проверьте XPath-селектор в методе parse.")

        for link in category_links:
            href = link.xpath('./@href').get()
            if href:
                yield response.follow(href, callback=self.parse_category_for_pagination)

    def parse_category_for_pagination(self, response):
        self.logger.info(f"Анализ пагинации для категории: {response.url}")
        last_page_link = response.xpath('//div[contains(@class, "nums")]/a[not(contains(@class, "arrow"))]/text()').getall()
        try:
            total_pages = int(last_page_link[-1]) if last_page_link else 1
            self.logger.info(f"Найдено {total_pages} страниц для категории {response.url}.")
        except (ValueError, IndexError):
            total_pages = 1
            self.logger.warning(f"Не удалось определить количество страниц для {response.url}, обрабатываем только первую.")

        # Запускаем запросы на все страницы пагинации одновременно
        for page_num in range(1, total_pages + 1):
            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)
            query_params['PAGEN_1'] = [str(page_num)]
            page_url = parsed_url._replace(query=urlencode(query_params, doseq=True)).geturl()
            yield scrapy.Request(page_url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        self.logger.info(f"Сбор товаров со страницы: {response.url}")
        
        product_links = response.xpath('//div[contains(@class, "catalog-block__info-title")]/a/@href').getall()
        for href in product_links:
            yield response.follow(href, callback=self.parse_product)
            
    def parse_product(self, response):
        if self.limit and self.item_count >= self.limit:
            return

        self.logger.info(f"Парсинг товара: {response.url} (Товар #{self.item_count + 1})")
        
        item = DentomirProductItem()
        
        # URL, Категория, Название, Артикул
        item['url'] = response.url
        breadcrumbs = response.xpath('//div[@id="navigation"]//span[@itemprop="name"]/text()').getall()
        item['category'] = ' / '.join([b.strip() for b in breadcrumbs[:-1] if b.strip()]) or None
        item['name'] = response.xpath('//h1/text()').get('').strip() or None
        item['sku'] = response.xpath('//div[contains(@class, "article__value")]/text()').get('').strip() or None

        # Описание
        description_parts = response.xpath('//div[@id="desc"]//text()').getall()
        item['description'] = '\n'.join([part.strip() for part in description_parts if part.strip()]) or None

        # Цена
        price = response.xpath('string(//div[contains(@class, "price--actual")]//span[contains(@class, "price_value")])').get() or \
                response.xpath('string(//div[contains(@class, "price__new")]/span[contains(@class, "price__new-val")])').get()
        clean_price = re.sub(r'\s+', ' ', price).strip() if price else None
        item['price_regular'] = clean_price
        item['price_discounted'] = clean_price

        # Бренд
        brand_raw = response.xpath('//div[contains(@class, "brand")]//a/img/@title').get() or \
                    response.xpath('//div[contains(@class, "brand-detail-info__title")]//a/text()').get()
        item['brand'] = brand_raw.strip() if brand_raw else None

        # Наличие
        availability_raw = response.xpath('//span[contains(@class, "status-container") and contains(@class, "instock")]//span[contains(@class, "js-replace-status")]/text()').get() or \
                           response.xpath('//div[contains(@class, "item-stock")]//span[contains(@class, "store_view")]/text()').get()
        item['availability'] = availability_raw.strip() if availability_raw else None

        # Рейтинг и количество отзывов
        item['rating'] = response.xpath('//div[contains(@class, "rating")]//*[contains(@class, "rating__value")]/text()').get('').strip() or None
        review_text = response.xpath('//div[contains(@class, "rating")]//a[contains(@class, "rating-link")]/text()').get() or \
                      response.xpath('//div[contains(@class, "rating")]//*[contains(@class, "rating__count")]/span/text()').get('')
        review_count_match = re.search(r'\d+', review_text)
        item['review_count'] = review_count_match.group(0) if review_count_match else None

        # Изображения
        image_hrefs = response.xpath('//div[contains(@class, "detail-gallery-big__item")]/a/@href').getall()
        item['image_urls'] = [response.urljoin(href) for href in image_hrefs] if image_hrefs else None

        # Увеличиваем счетчик и проверяем лимит
        self.item_count += 1
        yield item

        if self.limit and self.item_count >= self.limit:
            self.logger.info(f"Достигнут лимит в {self.limit} товаров. Завершение работы паука.")
            raise CloseSpider(f'Лимит {self.limit} товаров достигнут.')