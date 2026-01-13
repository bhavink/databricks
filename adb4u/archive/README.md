***REMOVED*** Archive - Legacy Content

**Status**: 📦 **ARCHIVED** - Reference Only

This folder contains legacy templates, scripts, and documentation from the original Azure Databricks repository.

**⚠️ For new deployments, use the modular structure in the main repository:**
- [New Modular Templates](../deployments/)
- [Current Documentation](../docs/)
- [Reusable Modules](../modules/)

---

***REMOVED******REMOVED*** 📂 Contents

***REMOVED******REMOVED******REMOVED*** Legacy Templates
- **`templates/`** - Original Terraform scripts (adb-npip, adb-pl-latest, adb-pvt-workspace)
- **`adb-arm-templates/`** - ARM templates for NPIP deployments

***REMOVED******REMOVED******REMOVED*** Demos & Examples
- **`accessing-adls/`** - ADLS Gen2 access examples (notebooks, SQL)
- **`adb-authenticating-rest-api/`** - Postman collections for AAD token authentication
- **`adb-e2e-automation-acelerator/`** - End-to-end automation examples
- **`users-groups-management/`** - User/group provisioning guides

***REMOVED******REMOVED******REMOVED*** SCIM & Service Principals
- **`adb-scim-provisioning-app-automation/`** - SCIM provisioning automation
- **`adb-service-principal-scim-api/`** - Service principal SCIM examples

***REMOVED******REMOVED******REMOVED*** Security & Deployment
- **`secure-deployments/`** - Data exfiltration prevention examples
- **`LEGACY-CONTENT.md`** - Original README content with Mermaid diagrams

---

***REMOVED******REMOVED*** 🔄 Migration Guide

***REMOVED******REMOVED******REMOVED*** Old vs New Structure

| Old Location | New Location | Status |
|--------------|--------------|--------|
| `templates/terraform-scripts/adb-npip/` | `deployments/non-pl/` | ✅ Replaced with modular version |
| `templates/terraform-scripts/adb-pl-latest/` | `deployments/full-private/` | 🚧 Coming soon |
| `secure-deployments/` | `docs/patterns/NON-PL.md` | ✅ Documented |
| Legacy README diagrams | `archive/LEGACY-CONTENT.md` | ✅ Archived |

***REMOVED******REMOVED******REMOVED*** Why Archive?

The legacy content:
- ❌ Uses monolithic Terraform files (not modular)
- ❌ Limited documentation
- ❌ No Unity Catalog support
- ❌ No BYOV (Bring Your Own VNet) support
- ❌ No comprehensive troubleshooting

The new modular structure:
- ✅ Modular, reusable Terraform components
- ✅ Comprehensive documentation (2,300+ lines)
- ✅ Unity Catalog mandatory
- ✅ BYOV support
- ✅ CMK support
- ✅ UML sequence diagrams
- ✅ Troubleshooting guides
- ✅ Pre-flight checklists

---

***REMOVED******REMOVED*** 📝 Using Legacy Templates

If you need to reference the legacy templates:

1. **Review** the archived content
2. **Compare** with new modular structure
3. **Migrate** to new templates (recommended)
4. **Document** any specific requirements not yet in new structure

**Do not use legacy templates for new deployments** - they lack modern features like Unity Catalog, CMK, and proper documentation.

---

***REMOVED******REMOVED*** 📚 Reference Links

**New Documentation**:
- [Quick Start Guide](../docs/01-QUICKSTART.md)
- [Troubleshooting Guide](../docs/TROUBLESHOOTING.md)
- [Traffic Flows](../docs/TRAFFIC-FLOWS.md)
- [Module Documentation](../docs/modules/)
- [Pattern Guides](../docs/patterns/)

**Legacy Documentation**:
- [Legacy Content](./LEGACY-CONTENT.md) - Original README diagrams

---

**Archived**: 2026-01-10  
**Original Content Date**: 2020-2024  
**Replacement Version**: 2.0 (Modular Structure)
