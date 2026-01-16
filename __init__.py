# __init__.py (Azure Function)
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import json
import os
from datetime import datetime
from ocr_invoice_processor import InvoiceOCRProcessor

def main(msg: func.QueueMessage, outputBlob: func.Out[str]) -> None:
    """
    Trigger Azure: processa fatture da coda messaggi
    """
    logging.info('Trigger Azure Function attivato')
    
    try:
        # Parse messaggio dalla coda
        message_body = json.loads(msg.get_body().decode('utf-8'))
        blob_url = message_body['blob_url']
        invoice_id = message_body['invoice_id']
        
        # Download blob
        blob_service = BlobServiceClient.from_connection_string(
            os.environ['AzureWebJobsStorage']
        )
        
        container_client = blob_service.get_container_client('invoices-raw')
        blob_client = container_client.get_blob_client(blob_url)
        
        # Download temporaneo
        temp_path = f'/tmp/{invoice_id}.pdf'
        with open(temp_path, 'wb') as download_file:
            download_file.write(blob_client.download_blob().readall())
        
        # Conversione PDF in immagine (se necessario)
        image_path = convert_pdf_to_image(temp_path)
        
        # Processo OCR
        processor = InvoiceOCRProcessor()
        invoice_data = processor.process_invoice(image_path)
        
        # Validazione dati
        validation_result = validate_invoice(invoice_data)
        
        # Preparazione output
        output_data = {
            'invoice_id': invoice_id,
            'processed_at': datetime.utcnow().isoformat(),
            'data': invoice_data.__dict__,
            'validation': validation_result,
            'status': 'ready_for_erp' if validation_result['is_valid'] else 'needs_review'
        }
        
        # Salva risultato in blob di output
        outputBlob.set(json.dumps(output_data))
        
        # Invia a coda ERP se valido
        if validation_result['is_valid']:
            send_to_erp_queue(output_data)
        
        logging.info(f'Fattura {invoice_id} processata con successo')
        
    except Exception as e:
        logging.error(f'Errore elaborazione: {str(e)}')
        raise

def convert_pdf_to_image(pdf_path: str) -> str:
    """Converti PDF in immagine per OCR"""
    from pdf2image import convert_from_path
    
    images = convert_from_path(pdf_path, dpi=300)
    image_path = pdf_path.replace('.pdf', '.png')
    images[0].save(image_path, 'PNG')
    return image_path

def validate_invoice(invoice_data) -> dict:
    """Validazione business logic"""
    errors = []
    
    if invoice_data.invoice_number == "N/A":
        errors.append("Numero fattura non rilevato")
    
    if invoice_data.total_amount <= 0:
        errors.append("Importo totale non valido")
    
    if invoice_data.confidence_score < 70:
        errors.append(f"Confidence OCR bassa: {invoice_data.confidence_score:.1f}%")
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'confidence': invoice_data.confidence_score
    }

def send_to_erp_queue(data: dict):
    """Invio a coda per integrazione ERP"""
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    
    connection_str = os.environ['ServiceBusConnection']
    client = ServiceBusClient.from_connection_string(connection_str)
    
    with client:
        sender = client.get_queue_sender(queue_name="erp-integration")
        message = ServiceBusMessage(json.dumps(data))
        sender.send_messages(message)
