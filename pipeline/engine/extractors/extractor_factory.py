from pipeline.engine.extractors.excel_extractor import ExcelExtractor
from pipeline.engine.extractors.pdf_extractor import PDFExtractor
from pipeline.engine.extractors.csv_extractor import CSVExtractor
from pipeline.engine.extractors.html_extractor import HTMLExtractor
from pipeline.engine.extractors.json_extractor import JSONExtractor

class ExtractorFactory:
    @staticmethod
    def get_extractor(file_format, config):
        fmt = file_format.lower()
        strategies = {
            'xlsx': ExcelExtractor,
            'xls': ExcelExtractor,
            'pdf': PDFExtractor,
            'csv': CSVExtractor,
            'html': HTMLExtractor,
            'json': JSONExtractor
        }
        
        if fmt not in strategies:
            raise ValueError(f"Unsupported file format for extraction: {file_format}")
            
        return strategies[fmt](config)
