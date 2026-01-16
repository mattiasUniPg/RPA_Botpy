# roi_calculator.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
import pandas as pd

@dataclass
class ROIMetrics:
    total_invoices_processed: int
    manual_time_saved_hours: float
    error_rate_reduction: float
    cost_savings_euro: float
    roi_percentage: float
    payback_months: float

class ROICalculator:
    def __init__(self):
        # Parametri di riferimento
        self.manual_processing_time_minutes = 15  # Tempo medio manuale
        self.hourly_cost_operator = 25  # Costo orario operatore
        self.error_rate_manual = 0.05  # 5% errori processo manuale
        self.error_rate_rpa = 0.005  # 0.5% errori processo RPA
        self.error_correction_cost = 50  # Costo medio correzione errore
        
    def calculate_roi(self, 
                     invoices_processed: int,
                     implementation_cost: float,
                     monthly_operational_cost: float,
                     months_in_operation: int) -> ROIMetrics:
        """Calcolo ROI dettagliato"""
        
        # Risparmio tempo
        time_saved_hours = (invoices_processed * self.manual_processing_time_minutes) / 60
        labor_savings = time_saved_hours * self.hourly_cost_operator
        
        # Risparmio errori
        errors_avoided = invoices_processed * (self.error_rate_manual - self.error_rate_rpa)
        error_savings = errors_avoided * self.error_correction_cost
        
        # Costi totali
        total_costs = implementation_cost + (monthly_operational_cost * months_in_operation)
        
        # Benefici totali
        total_benefits = labor_savings + error_savings
        
        # ROI
        roi_percentage = ((total_benefits - total_costs) / total_costs) * 100
        
        # Payback period
        monthly_savings = total_benefits / months_in_operation
        payback_months = implementation_cost / monthly_savings if monthly_savings > 0 else float('inf')
        
        return ROIMetrics(
            total_invoices_processed=invoices_processed,
            manual_time_saved_hours=time_saved_hours,
            error_rate_reduction=(self.error_rate_manual - self.error_rate_rpa) * 100,
            cost_savings_euro=total_benefits - total_costs,
            roi_percentage=roi_percentage,
            payback_months=payback_months
        )
    
    def generate_report(self, metrics: ROIMetrics) -> str:
        """Generazione report ROI testuale"""
        return f"""
╔════════════════════════════════════════════════════╗
║           REPORT ROI - AUTOMAZIONE RPA             ║
╚════════════════════════════════════════════════════╝

📊 METRICHE OPERATIVE
  • Fatture processate: {metrics.total_invoices_processed:,}
  • Ore risparmiate: {metrics.manual_time_saved_hours:,.1f}h
  • Riduzione errori: {metrics.error_rate_reduction:.1f}%

💰 IMPATTO ECONOMICO
  • Risparmio totale: €{metrics.cost_savings_euro:,.2f}
  • ROI: {metrics.roi_percentage:+.1f}%
  • Payback period: {metrics.payback_months:.1f} mesi

✨ EFFICIENZA: +{(metrics.roi_percentage/100*35):.0f}% 
   (Target benchmark: +35% come Nubys)
"""

# Esempio di utilizzo
if __name__ == "__main__":
    calculator = ROICalculator()
    
    # Scenario reale: 6 mesi di operatività
    metrics = calculator.calculate_roi(
        invoices_processed=5000,
        implementation_cost=50000,
        monthly_operational_cost=2000,
        months_in_operation=6
    )
    
    print(calculator.generate_report(metrics))
