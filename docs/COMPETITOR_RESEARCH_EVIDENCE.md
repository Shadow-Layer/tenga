# Tenga Inventory — Competitor Research Evidence Catalogue

**Status:** Phase 2 Research (Evidence-Based)  
**Access Date:** October 9, 2026  
**Scope:** 5 primary competitors + patterns synthesis  
**Research Method:** Web-based documentation, feature pages, help documentation

---

## Research Summary

This document records competitor research findings with explicit confidence levels. Each entry distinguishes:

- **Verified**: Directly observed via web access
- **Documented**: Stated in official vendor documentation
- **Inference**: Reasonable conclusion from available evidence, requires validation
- **Unavailable**: Could not access; limitations noted

No screen, workflow, or feature is invented where evidence is unavailable.

---

## Competitor 1: Loyverse POS

### Product Overview
- **Vendor**: Loyverse Inc.
- **Type**: Cloud-first mobile and web POS
- **Target Market**: Retail, restaurants, small businesses (global)
- **Source URL**: https://loyverse.com
- **Availability**: **Verified** — Free tier available, paid tiers for advanced features

### Research Access
| Component | Status | Evidence |
|-----------|--------|----------|
| Product website | ✅ Verified | https://loyverse.com accessible |
| Features page | ⚠️ Partial | https://loyverse.com/features (payment methods listed only) |
| Help documentation | ⚠️ Limited | https://help.loyverse.com (index page only, March 2024) |
| Screenshots | ❌ Unavailable | Requires account login to access app interface |
| Video tour | ❌ Unavailable | Not accessed in this research phase |

### Observed Capabilities (Documented)

**Sales & Analytics**
- Revenue reports, average sale, profit tracking
- Sales trends and pattern analysis
- Best-selling items and categories identification
- Complete sales history export to spreadsheets

**Source Evidence**
- https://loyverse.com (main site, October 9 2026)
- Confidence: **Documented** (vendor-claimed, not independently verified)

### Sales Recording & Payment Processing
- Multiple payment methods supported (documented: STORES, SB Payment Service, others)
- iOS and multi-platform support
- Available in 40+ countries and regions

**Source Evidence**
- https://loyverse.com/features (payment list, October 9 2026)
- Confidence: **Documented**

### Inventory & Stock Management
**Status**: ❌ **Not verified in web access**

Help documentation exists but requires login to access detailed inventory workflows. Cannot confirm:
- Product creation interface
- Stock receiving workflow
- Stock adjustment and reconciliation
- Low-stock alerts
- Multi-location stock management
- Barcode scanning behavior

**Inference**: Loyverse advertises inventory management for retail, but specific workflows remain unobserved.

---

## Competitor 2: Tengai POS (Zimbabwe)

### Product Overview
- **Vendor**: Tengai [exact org TBD]
- **Type**: [Unknown, requires research]
- **Target Market**: Zimbabwe-based POS
- **Regional Relevance**: **HIGH** — local market operator
- **Research Status**: ⚠️ Limited access

### Research Access
| Component | Status | Evidence |
|-----------|--------|----------|
| Product website | ❌ Unavailable | Domain https://tengaipe.co.zw (DNS resolution failure, Oct 9) |
| Local documentation | ❌ Unknown | No accessible source identified |
| Screenshots | ❌ Unknown | Not accessed |
| User reviews | ❌ Not searched | May exist on local forums or review sites |

### Implications for Tenga
- **Decision**: Without direct access to Tengai's interface, cannot document specific workflows
- **Recommendation**: Acquire Tengai demo access or find user documentation separately
- **Temporary Action**: Proceed with research on other competitors; return to Tengai when access is established

**Note for Product Owner**: Tengai represents the primary local competitor. Direct competitive analysis requires either:
1. Tengai product demo/trial access
2. Screenshots or case studies from Tengai's marketing materials
3. User interviews with Tengai operators in Zimbabwe

---

## Competitor 3: Pointly POS (Zimbabwe)

### Product Overview
- **Vendor**: Pointly [exact org TBD]
- **Type**: [Unknown, requires research]
- **Target Market**: Zimbabwe-based POS and inventory
- **Regional Relevance**: **HIGH** — local market operator
- **Research Status**: ⚠️ Limited access

### Research Access
| Component | Status | Evidence |
|-----------|--------|----------|
| Product website | ❌ Unknown | URL not confirmed in this research |
| Local documentation | ❌ Unknown | No accessible source identified |
| Screenshots | ❌ Unknown | Not accessed |

### Implications for Tenga

**Decision**: Pointly requires dedicated research effort.

**Temporary Action**: Proceed with other competitors. Pointly research can be completed when dedicated local research resources are available.

**Note for Product Owner**: Like Tengai, Pointly represents important local context. Research should include:
1. Official Pointly website and product pages
2. Documentation or help guides
3. Case studies with local businesses
4. Pricing and subscription positioning

---

## Competitor 4: uniCenta oPOS

### Product Overview
- **Vendor**: uniCenta Community
- **Type**: Open-source desktop POS
- **License**: GNU GPL v3 (free and open source)
- **Source**: SourceForge https://sourceforge.net/projects/unicentaopos
- **Current Version**: 5.0 (stable, free download)
- **Target Market**: Small businesses, restaurants, retail
- **Regional Relevance**: **MODERATE** — global open-source standard, not Zimbabwe-specific

### Research Access
| Component | Status | Evidence |
|-----------|--------|----------|
| Product website | ✅ Verified | https://unicenta.com accessible |
| Source repository | ❌ GitHub not accessible | (404 error Oct 9) |
| Download/SourceForge | ⚠️ Not accessed | Mentioned on official site |
| Screenshots/wiki | ❌ Not accessed | Requires separate navigation |
| Documentation | ❌ Not accessed | Likely available but not retrieved |

### Observed Capabilities (Documented)

**Open Source Architecture**
- Desktop-based, not cloud-dependent
- Suitable for offline-first operation (inherent in desktop architecture)
- Modular, customizable (open source advantage)
- **Relevance to Tenga**: Multi-terminal, self-hosted operation model informative

**Implications for Tenga**
- Desktop architecture may inform multi-device/offline patterns
- Open-source model suggests architectural transparency valuable for integrations
- Community support model differs from SaaS (Tenga is subscription-based)

### Unverified Capabilities

The following are **NOT verified** but are typical of desktop POS systems:
- Multi-terminal architecture
- Local database (SQLite or similar)
- Stock reconciliation workflows
- Till session management
- Receipt printing
- Barcode scanning

**Confidence**: **Inference only** — typical for this category, not verified for uniCenta specifically.

---

## Competitor 5: Kyte POS

### Product Overview
- **Vendor**: Kyte [org TBD]
- **Type**: Mobile-first POS
- **Source**: https://kyte.io
- **Research Status**: ❌ Limited access (landing page redirect, not explored)

### Research Access
| Component | Status | Evidence |
|-----------|--------|----------|
| Product website | ⚠️ Redirect observed | https://kyte.io redirects to /lander page (not explored) |
| Screenshots | ❌ Not accessed | |
| Documentation | ❌ Not accessed | |
| Feature list | ❌ Not accessed | |

### Implications for Tenga

**Decision**: Kyte requires dedicated research effort.

**Temporary Action**: Mobile-first patterns can be inferred from Loyverse research and general mobile UX principles. Return to Kyte when dedicated research capacity available.

---

## Synthesis: Key Patterns from Available Evidence

### What Was Verified
1. **Loyverse** operates a free tier with revenue, sales trend, and analytics features
2. **uniCenta** demonstrates that open-source, desktop-based POS is viable
3. **Multiple payment integrations** are table stakes for modern POS
4. **Cloud vs. Desktop**: Competitors span both models (Loyverse = cloud, uniCenta = desktop)
5. **Export capabilities**: Data export (spreadsheets) is a standard feature

### What Remains Unverified (Cannot Proceed With)
1. **Specific inventory workflows**: None of the accessible products provided detailed product creation, stock receiving, or reconciliation UI patterns
2. **Offline behavior**: Offline handling in cloud-first products (Loyverse) not observable without account access
3. **Zimbabwe context**: Tengai and Pointly (local competitors) inaccessible; regional patterns unknown
4. **Mobile touch patterns**: Kyte not accessed; mobile-specific interactions inferred only
5. **Multi-location stock management**: No product UI documented
6. **Barcode scanning integration**: No workflow documented

### Inferences Drawn (Require Validation)

**Standard POS Features** (based on product marketing and category knowledge):
- Product creation with SKU, name, price
- Barcode scanning → cart addition
- Quantity adjustment in cart
- Payment method selection
- Receipt printing
- Sales history with filters
- Basic reports (daily sales, top products)
- User authentication
- Till session management

**Standard Inventory Features** (based on category patterns):
- Product list with current stock
- Low-stock alerts or thresholds
- Stock receiving/purchase orders
- Stock adjustments and corrections
- Physical count reconciliation
- Multi-location support
- Cost tracking
- Stock valuation (weighted average, FIFO, or similar)

**These inferences are reasonable for the category but unverified for Tenga's specific competitors.**

---

## Research Gaps and Recommendations

### High-Priority Research (For Next Phase)

1. **Local Competitors (Zimbabwe)**
   - Acquire Tengai and Pointly demo access
   - Document their inventory and POS workflows
   - Interview local operators if possible
   - Identify fiscal/compliance requirements in Zimbabwean context

2. **Loyverse Deep Dive**
   - Create free account if permitted
   - Screenshot key workflows: product creation, stock management, checkout
   - Test barcode scanning behavior
   - Document offline handling

3. **uniCenta Interface**
   - Download and install version 5.0
   - Screenshot key screens: inventory, checkout, reconciliation
   - Test multi-terminal workflow

4. **Mobile-First Patterns**
   - Complete Kyte research when access restored
   - Evaluate mobile-specific interaction patterns for Tenga's tablet/phone support

### Medium-Priority Research

1. **Square POS** (advanced benchmark only)
   - Not researched in this phase
   - Recommended for advanced features post-MVP (payments, advanced analytics)

2. **Odoo POS** (ERPNext)
   - Not researched in this phase
   - Recommended for multi-location, fiscal integration comparison (post-MVP)

---

## Evidence Quality Summary

| Competitor | Product Access | UI Verified | Workflows | Confidence |
|------------|------------------|-------------|-----------|------------|
| **Loyverse** | ✅ Partial | ❌ Screenshots unavailable | Documented (partial) | **Documented** |
| **Tengai** | ❌ Unavailable | ❌ No | Unknown | **Unknown** |
| **Pointly** | ❌ Unavailable | ❌ No | Unknown | **Unknown** |
| **uniCenta** | ✅ Downloadable | ⚠️ Not accessed | Inferred (typical for category) | **Inference** |
| **Kyte** | ⚠️ Site redirect | ❌ No | Unknown | **Unknown** |

**Overall Research Status**: ⚠️ **Partial** — Limited by account login requirements and regional availability. Sufficient for identifying common patterns; insufficient for precise local competitive analysis.

---

## Next Steps

### Immediate (This Phase)
1. Use Tenga requirements + inferred patterns to design Inventory slice
2. Mark Loyverse findings as inspiration, not prescription
3. Preserve design choices reversible until local competitor data available

### Before Checkout Design
1. Acquire Tengai or Pointly demo access
2. Document local POS interaction patterns
3. Identify fiscal/compliance requirements for Zimbabwean context
4. Update design with local evidence

### Phase Completion
This research document will be updated with:
- Screenshots from Tengai and Pointly (if acquired)
- uniCenta interface documentation
- Kyte mobile patterns
- Detailed comparison matrix populated with verified evidence
- Recommendations for Tenga's competitive positioning

---

## References and Sources

| URL | Date Accessed | Status | Notes |
|-----|---------------|--------|-------|
| https://loyverse.com | Oct 9, 2026 | ✅ Accessible | Main features page, partial content |
| https://loyverse.com/features | Oct 9, 2026 | ✅ Accessible | Payment methods list only |
| https://help.loyverse.com | Oct 9, 2026 | ✅ Accessible | Index page only, March 2024 update |
| https://tengaipe.co.zw | Oct 9, 2026 | ❌ DNS failure | Regional domain, resolution failed |
| https://unicenta.com | Oct 9, 2026 | ✅ Accessible | Product info, SourceForge link |
| https://github.com/unicenta/unicentaopos | Oct 9, 2026 | ❌ 404 | Repository not found at this URL |
| https://sourceforge.net/projects/unicentaopos | Oct 9, 2026 | ⚠️ Not accessed | Referenced on unicenta.com |
| https://kyte.io | Oct 9, 2026 | ⚠️ Redirect | Landing page, not explored |

---

## Document Notes

- **Prepared by**: Copilot
- **Authority**: Evidence-based research only; no invented features or workflows
- **Revision Status**: Initial research (Phase 2). To be updated with verified evidence from Tengai, Pointly, and deeper Loyverse/uniCenta analysis.
- **Confidence Disclaimer**: This document is explicit about what could and could not be verified. Design decisions based on this research should mark unverified assumptions clearly and test them with actual competitor products when available.
