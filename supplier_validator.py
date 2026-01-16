# supplier_validator.py
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import json

class SupplierSpider(scrapy.Spider):
    name = 'supplier_validator'
    
    def __init__(self, vat_number: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vat_number = vat_number
        self.start_urls = [
            f'https://www.registroimprese.it/ricerca?q={vat_number}',
            f'https://openapi.agenziaentrate.gov.it/vies/v1/verify/{vat_number}'
        ]
    
    def parse(self, response):
        """Estrazione dati fornitore da fonti pubbliche"""
        if 'registroimprese' in response.url:
            yield {
                'vat_number': self.vat_number,
                'company_name': response.css('.company-name::text').get(),
                'legal_status': response.css('.status::text').get(),
                'address': response.css('.address::text').get(),
                'source': 'registro_imprese'
            }
        
        elif 'agenziaentrate' in response.url:
            data = json.loads(response.text)
            yield {
                'vat_number': self.vat_number,
                'valid': data.get('valid', False),
                'company_name': data.get('name', ''),
                'source': 'vies'
            }

class SupplierValidator:
    def validate_supplier(self, vat_number: str) -> dict:
        """Validazione fornitore tramite scraping"""
        results = []
        
        process = CrawlerProcess({
            'USER_AGENT': 'RPA-Bot/1.0',
            'ROBOTSTXT_OBEY': True,
            'CONCURRENT_REQUESTS': 1,
            'DOWNLOAD_DELAY': 2
        })
        
        def collect_results(item):
            results.append(item)
        
        process.crawl(SupplierSpider, vat_number=vat_number)
        process.start()
        
        return {
            'vat_number': vat_number,
            'validation_results': results,
            'is_valid': any(r.get('valid', False) for r in results)
        }
