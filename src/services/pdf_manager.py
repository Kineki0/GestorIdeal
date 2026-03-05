# pdf_manager.py
from fpdf import FPDF
import io
import pandas as pd

class LeadPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Ficha do Lead - Gestor Ideal', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generate_lead_pdf(p):
    """Gera um PDF formatado com os dados do lead."""
    pdf = LeadPDF()
    pdf.add_page()
    pdf.set_font('helvetica', '', 12)

    # Dados Básicos
    pdf.set_fill_color(230, 240, 255)
    pdf.cell(0, 10, 'Dados Cadastrais', 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    fields = [
        ('ID do Lead', str(p.get('ID_Lead', 'N/A'))),
        ('Razão Social', str(p.get('Razao_Social', 'N/A'))),
        ('CNPJ', str(p.get('CNPJ', 'N/A'))),
        ('E-mail', str(p.get('Email', 'N/A'))),
        ('Contato', str(p.get('Nome_Contato', 'N/A'))),
        ('Prioridade', str(p.get('Prioridade', 'N/A'))),
        ('Etapa Atual', str(p.get('Etapa_Atual', 'N/A'))),
        ('Data Criação', str(p.get('Data_Criacao', 'N/A'))),
    ]

    for label, val in fields:
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(40, 8, f'{label}:', 0)
        pdf.set_font('helvetica', '', 10)
        pdf.cell(0, 8, val, 0, 1)

    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 10, 'Descrição / Observações:', 0, 1)
    pdf.set_font('helvetica', '', 10)
    pdf.multi_cell(0, 8, str(p.get('Descricao', 'Sem descrição.')))

    return bytes(pdf.output())
