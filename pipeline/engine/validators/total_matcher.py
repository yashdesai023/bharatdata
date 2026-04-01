import logging

class TotalMatcher:
    def __init__(self, tolerance=0.1):
        self.tolerance = tolerance
        self.logger = logging.getLogger("TotalMatcher")

    def validate(self, records, summary_row, fields_to_sum):
        """
        Verifies that the sum of 'fields_to_sum' across 'records' matches 'summary_row'.
        fields_to_sum: List of internal field names to verify.
        """
        if not summary_row:
            self.logger.warning("No summary row provided for validation. Skipping mathematical parity check.")
            return True

        errors = []
        for field in fields_to_sum:
            target = summary_row.get(field)
            if target is None:
                self.logger.debug(f"Field '{field}' not found in summary row. Skipping.")
                continue

            # Convert to float for math
            try:
                target_val = float(str(target).replace(',', ''))
            except (ValueError, TypeError):
                self.logger.warning(f"Could not convert summary value '{target}' for field '{field}' to float.")
                continue

            actual_sum = 0.0
            for r in records:
                val = r.get(field, 0)
                try:
                    actual_sum += float(str(val).replace(',', '')) if val is not None else 0.0
                except (ValueError, TypeError):
                    pass

            diff = abs(actual_sum - target_val)
            if diff > self.tolerance:
                msg = f"PARITY FAILURE in '{field}': Sum of rows ({actual_sum}) != Gov Total ({target_val}). Discrepancy: {diff}"
                self.logger.error(msg)
                errors.append(msg)
            else:
                self.logger.info(f"PARITY OK for '{field}': {actual_sum} matches {target_val}")

        if errors:
            raise ValueError(" | ".join(errors))
            
        return True
