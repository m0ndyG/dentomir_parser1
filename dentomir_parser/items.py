import scrapy

class DentomirProductItem(scrapy.Item):
    url = scrapy.Field()                
    category = scrapy.Field()           
    name = scrapy.Field()               
    sku = scrapy.Field()                
    description = scrapy.Field()        
    price_regular = scrapy.Field()      
    price_discounted = scrapy.Field()   
    brand = scrapy.Field()              
    availability = scrapy.Field()       
    rating = scrapy.Field()             
    review_count = scrapy.Field()       
    image_urls = scrapy.Field()         