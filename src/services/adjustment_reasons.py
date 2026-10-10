"""Adjustment reason mapping and validation service.

This module manages the mapping between user-facing labels and backend canonical reason codes.
The backend uses uppercase canonical codes for audit trail consistency.
The frontend uses user-friendly labels for UI display.

Canonical reason codes (accepted by backend):
- PHYSICAL_COUNT_DISCREPANCY: Physical inventory count doesn't match system
- DAMAGE: Product was damaged and removed from inventory
- SHRINKAGE: Loss due to theft, evaporation, or other shrinkage
- ADJUSTMENT: Generic inventory adjustment
"""

# Canonical reason codes recognized by the backend
CANONICAL_REASON_CODES = {
    "PHYSICAL_COUNT_DISCREPANCY",
    "DAMAGE",
    "SHRINKAGE",
    "ADJUSTMENT",
}

# Mapping from frontend labels to canonical codes
LABEL_TO_CODE = {
    "Physical Count Discrepancy": "PHYSICAL_COUNT_DISCREPANCY",
    "Damage": "DAMAGE",
    "Shrinkage": "SHRINKAGE",
    "Adjustment": "ADJUSTMENT",
    # Also accept direct canonical codes
    "PHYSICAL_COUNT_DISCREPANCY": "PHYSICAL_COUNT_DISCREPANCY",
    "DAMAGE": "DAMAGE",
    "SHRINKAGE": "SHRINKAGE",
    "ADJUSTMENT": "ADJUSTMENT",
}

# Reverse mapping for display purposes
CODE_TO_LABEL = {v: k for k, v in LABEL_TO_CODE.items() if not v == k}


def validate_and_normalize_reason(reason: str) -> str:
    """Validate and normalize an adjustment reason.
    
    Converts user-friendly frontend labels to canonical backend codes.
    Rejects unsupported values rather than silently translating to a different meaning.
    
    Args:
        reason: The reason string (may be a label or canonical code)
        
    Returns:
        The canonical reason code
        
    Raises:
        ValueError: If the reason is not a recognized label or canonical code
    """
    if not reason:
        raise ValueError("Reason cannot be empty")
    
    # Try to find in the mapping
    normalized = LABEL_TO_CODE.get(reason)
    if normalized:
        return normalized
    
    # If not found, reject it
    raise ValueError(
        f"Unsupported reason: '{reason}'. "
        f"Accepted codes: {', '.join(sorted(CANONICAL_REASON_CODES))}"
    )


def get_label_for_code(code: str) -> str:
    """Get user-friendly label for a canonical code.
    
    Args:
        code: The canonical reason code
        
    Returns:
        User-friendly label for display
        
    Raises:
        ValueError: If the code is not recognized
    """
    if code not in CANONICAL_REASON_CODES:
        raise ValueError(f"Unknown reason code: {code}")
    
    return CODE_TO_LABEL.get(code, code)


def list_canonical_codes() -> list:
    """Get list of all canonical reason codes."""
    return sorted(list(CANONICAL_REASON_CODES))


def list_labels() -> list:
    """Get list of all user-friendly labels."""
    # Return only the non-canonical-code keys
    return sorted([k for k in LABEL_TO_CODE.keys() if k not in CANONICAL_REASON_CODES])
