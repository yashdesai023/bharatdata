import re

class TypeEnforcer:
    @staticmethod
    def to_int(value):
        """Converts raw value to integer, handling Indian comma notation."""
        if value is None: return None
        str_val = str(value).strip()
        # Remove commas, spaces, currency symbols
        str_val = re.sub(r'[, \u20B9\u00A0]', '', str_val)
        try:
            return int(float(str_val)) # Handle "100.0" as well
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def to_float(value):
        """Converts raw value to float, stripping '%' if necessary."""
        if value is None: return None
        str_val = str(value).strip().replace('%', '')
        str_val = re.sub(r'[, \u20B9\u00A0]', '', str_val)
        try:
            return float(str_val)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def to_bool(value):
        """Converts raw value to boolean."""
        if value is None: return False
        str_val = str(value).strip().lower()
        if str_val in ['yes', 'y', 'true', '1', '1.0']:
            return True
        return False
