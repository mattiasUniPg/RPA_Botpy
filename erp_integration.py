# erp_integration.py
import requests
from typing import Dict
import logging
from dataclasses import asdict

class ERPIntegrator:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        self.logger = logging.getLogger(__name__)
    
    def create_invoice(self, invoice_data: Dict) -> Dict:
        """Creazione fattura in ERP"""
        endpoint = f"{self.base_url}/api/invoices"
        
        # Mapping dati per formato ERP
        erp_payload = {
            'DocumentType': 'Invoice',
            'DocumentNumber': invoice_data['invoice_number'],
            'PostingDate': invoice_data['invoice_date'],
            'BusinessPartner': invoice_data['supplier_name'],
            'TaxIdentification': invoice_data['vat_number'],
            'DocumentTotal': invoice_data['total_amount'],
            'TaxTotal': invoice_data['vat_amount'],
            'DocumentLines': invoice_data.get('line_items', [])
        }
        
        try:
            response = requests.post(
                endpoint,
                json=erp_payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            self.logger.info(f"Fattura {invoice_data['invoice_number']} creata in ERP")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Errore integrazione ERP: {str(e)}")
            raise
    
    def check_duplicate(self, invoice_number: str) -> bool:
        """Verifica duplicati in ERP"""
        endpoint = f"{self.base_url}/api/invoices"
        params = {'$filter': f"DocumentNumber eq '{invoice_number}'"}
        
        response = requests.get(endpoint, headers=self.headers, params=params)
        data = response.json()
        
        return len(data.get('value', [])) > 0
