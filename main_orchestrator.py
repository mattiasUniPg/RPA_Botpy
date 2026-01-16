# main_orchestrator.py
import asyncio
from typing import List
import logging
from datetime import datetime

class RPAOrchestrator:
    def __init__(self):
        self.ocr_processor = InvoiceOCRProcessor()
        self.erp_integrator = ERPIntegrator(
            base_url=os.getenv('ERP_URL'),
            api_key=os.getenv('ERP_API_KEY')
        )
        self.supplier_validator = SupplierValidator()
        self.roi_calculator = ROICalculator()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def process_invoice_pipeline(self, invoice_path: str) -> dict:
        """Pipeline completa di elaborazione"""
        start_time = datetime.now()
        
        try:
            # Step 1: OCR
            self.logger.info("Step 1: Estrazione dati OCR")
            invoice_data = self.ocr_processor.process_invoice(invoice_path)
            
            # Step 2: Validazione fornitore
            self.logger.info("Step 2: Validazione fornitore")
            validation = self.supplier_validator.validate_supplier(
                invoice_data.vat_number
            )
            
            # Step 3: Check duplicati
            self.logger.info("Step 3: Verifica duplicati")
            is_duplicate = self.erp_integrator.check_duplicate(
                invoice_data.invoice_number
            )
            
            if is_duplicate:
                return {
                    'status': 'duplicate',
                    'message': 'Fattura già presente in sistema'
                }
            
            # Step 4: Integrazione ERP
            self.logger.info("Step 4: Creazione in ERP")
            erp_response = self.erp_integrator.create_invoice(
                asdict(invoice_data)
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'invoice_number': invoice_data.invoice_number,
                'erp_id': erp_response.get('id'),
                'processing_time_seconds': processing_time,
                'confidence': invoice_data.confidence_score
            }
            
        except Exception as e:
            self.logger.error(f"Errore pipeline: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
