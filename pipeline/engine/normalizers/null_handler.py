class NullHandler:
    def __init__(self, null_markers=None):
        self.null_markers = null_markers or ["-", "NA", "@", "null", "nil", "", "none"]

    def handle(self, value, strategy="null"):
        """
        Maps a raw missing value marker to either None or 0 based on strategy.
        strategy: "zero" (empty -> 0) or "null" (empty -> None)
        """
        if value is None:
            return 0 if strategy == "zero" else None
        
        str_val = str(value).strip().lower()
        
        # Check if the value is in our known null markers
        if any(str_val == marker.lower() for marker in self.null_markers):
            return 0 if strategy == "zero" else None
        
        return value
