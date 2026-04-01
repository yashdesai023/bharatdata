class ConsistencyChecker:
    def __init__(self, rules):
        """
        rules: list of dicts like: 
        {'expr': 'A + B == C', 'fields': ['A', 'B', 'C']}
        """
        self.rules = rules

    def validate(self, records):
        """Applies logical consistency rules to each record."""
        errors = []
        for idx, record in enumerate(records):
            for rule in self.rules:
                expr = rule.get('expr')
                # Use a safe eval-like check for basic arithmetic
                # In real engine, we'd use a more robust parser
                try:
                    # Replace field names with their values
                    eval_expr = expr
                    for field in rule.get('fields', []):
                        val = str(record.get(field, 0))
                        eval_expr = eval_expr.replace(field, val)
                    
                    if not eval(eval_expr): # Only for internal, trusted rules
                        errors.append(f"Row {idx+1}: Consistency Breach [{expr}] -> {eval_expr}")
                except Exception as e:
                    errors.append(f"Row {idx+1}: Error in rule {expr}: {e}")
        
        if errors:
            raise ValueError("Consistency Violation: " + " | ".join(errors[:3]))
            
        return True
