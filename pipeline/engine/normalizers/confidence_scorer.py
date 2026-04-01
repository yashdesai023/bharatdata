class ConfidenceScorer:
    def __init__(self, base_scores=None):
        self.base_scores = base_scores or {
            'xlsx': 1.0,
            'xls': 1.0,
            'csv': 1.0,
            'json': 1.0,
            'pdf': 0.9,
            'html': 0.8
        }

    def calculate(self, file_format, deductions=0.0):
        """
        Calculates a confidence score.
        Deductions: total sum of confidence point deductions from other layers.
        """
        fmt = str(file_format).lower()
        base = self.base_scores.get(fmt, 0.7)
        
        # Multiply to penalize dirty data
        score = base - deductions
        return max(0.0, min(1.0, score)) # Clamp between 0 and 1
        
