CATEGORY_MAP = {
    # IPC Crimes
    "total cognizable ipc crimes": "ipc_total",
    "total ipc crimes": "ipc_total",
    "ipc crimes": "ipc_total",
    
    # SLL Crimes
    "total cognizable sll crimes": "sll_total",
    "total sll crimes": "sll_total",
    "sll crimes": "sll_total",
    
    # Total Crimes
    "total cognizable crimes": "total_crimes",
    "total crimes": "total_crimes",
    
    # Known missing variants (add here as needed)
    "unknown category (implied by filename)": "unknown",
    "unknown pdf category": "unknown"
}

def map_category(raw_category: str) -> str:
    """Maps the verbose textual category header to an expected slug format"""
    if not isinstance(raw_category, str):
        return "unknown"
        
    cleaned = raw_category.strip().lower()
    
    # Exact match
    for k, v in CATEGORY_MAP.items():
        if k == cleaned:
            return v
            
    # Substring match
    for k, v in CATEGORY_MAP.items():
        if k in cleaned:
            return v
            
    # Slugify fallback
    slug = cleaned.replace(" ", "_").replace("/", "_").replace("-", "_")
    return slug[:50] # DB schema might cap size
