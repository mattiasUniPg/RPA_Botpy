# ocr_invoice_processor.py
import cv2
import pytesseract
import numpy as np
from PIL import Image
import re
from dataclasses import dataclass
from typing import Optional, List
import logging

@dataclass
class InvoiceData:
    invoice_number: str
    invoice_date: str
    supplier_name: str
    vat_number: str
    total_amount: float
    vat_amount: float
    line_items: List[dict]
    confidence_score: float

class InvoiceOCRProcessor:
    def __init__(self, tesseract_path: str = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        self.logger = logging.getLogger(__name__)
        
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocessing avanzato per migliorare l'accuratezza OCR"""
        img = cv2.imread(image_path)
        
        # Conversione in scala di grigi
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Riduzione rumore
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Binarizzazione adattiva
        binary = cv2.adaptiveThreshold(
            denoised, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Deskewing (correzione inclinazione)
        coords = np.column_stack(np.where(binary > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        (h, w) = binary.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            binary, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        return rotated
    
    def extract_text_with_layout(self, image: np.ndarray) -> dict:
        """Estrazione testo con informazioni di layout"""
        # OCR con dati di posizione
        custom_config = r'--oem 3 --psm 6'
        data = pytesseract.image_to_data(
            image, 
            output_type=pytesseract.Output.DICT,
            config=custom_config,
            lang='ita+eng'
        )
        
        return data
    
    def extract_invoice_number(self, text: str) -> Optional[str]:
        """Estrazione numero fattura con pattern multipli"""
        patterns = [
            r'(?:fattura|invoice|n[°\.º]?)\s*[:\-]?\s*(\d{4,}[/\-]?\d*)',
            r'(?:FT|INV)[:\-\s]*(\d{4,})',
            r'numero\s+fattura[:\s]+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def extract_date(self, text: str) -> Optional[str]:
        """Estrazione data con formati multipli"""
        patterns = [
            r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'(\d{2,4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def extract_vat_number(self, text: str) -> Optional[str]:
        """Estrazione Partita IVA italiana"""
        pattern = r'(?:p\.?\s*iva|partita\s+iva)[:\s]*(\d{11})'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else None
    
    def extract_amounts(self, text: str) -> dict:
        """Estrazione importi con gestione formati europei"""
        amounts = {
            'total': None,
            'vat': None,
            'subtotal': None
        }
        
        # Pattern per importi (formato europeo: 1.234,56)
        total_pattern = r'(?:totale|total)[:\s]+€?\s*([\d\.,]+)'
        vat_pattern = r'(?:iva|vat)[:\s]+€?\s*([\d\.,]+)'
        
        total_match = re.search(total_pattern, text, re.IGNORECASE)
        if total_match:
            amount_str = total_match.group(1).replace('.', '').replace(',', '.')
            amounts['total'] = float(amount_str)
        
        vat_match = re.search(vat_pattern, text, re.IGNORECASE)
        if vat_match:
            amount_str = vat_match.group(1).replace('.', '').replace(',', '.')
            amounts['vat'] = float(amount_str)
            
        return amounts
    
    def process_invoice(self, image_path: str) -> InvoiceData:
        """Pipeline completa di elaborazione fattura"""
        self.logger.info(f"Elaborazione fattura: {image_path}")
        
        # Preprocessing
        processed_img = self.preprocess_image(image_path)
        
        # OCR con layout
        ocr_data = self.extract_text_with_layout(processed_img)
        full_text = pytesseract.image_to_string(processed_img, lang='ita+eng')
        
        # Estrazione dati strutturati
        invoice_number = self.extract_invoice_number(full_text)
        invoice_date = self.extract_date(full_text)
        vat_number = self.extract_vat_number(full_text)
        amounts = self.extract_amounts(full_text)
        
        # Calcolo confidence score medio
        confidences = [conf for conf in ocr_data['conf'] if conf != -1]
        avg_confidence = np.mean(confidences) if confidences else 0
        
        return InvoiceData(
            invoice_number=invoice_number or "N/A",
            invoice_date=invoice_date or "N/A",
            supplier_name=self._extract_supplier(full_text),
            vat_number=vat_number or "N/A",
            total_amount=amounts.get('total', 0.0),
            vat_amount=amounts.get('vat', 0.0),
            line_items=[],
            confidence_score=avg_confidence
        )
    
    def _extract_supplier(self, text: str) -> str:
        """Estrazione nome fornitore (prime righe del documento)"""
        lines = text.split('\n')
        # Prendi le prime 5 righe non vuote
        supplier_lines = [line.strip() for line in lines[:10] if line.strip()]
        return supplier_lines[0] if supplier_lines else "N/A"
