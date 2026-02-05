# Thermal MCP Server Examples

This directory contains professional validation and usage examples for the Thermal MCP Server.

## Current Examples

### `validation_nvidia_h100.py` - Model Validation
**Purpose**: Prove engineering credibility by reproducing published NVIDIA H100 GPU thermal data.

**What it demonstrates:**
- Validation against real hardware specifications
- Single GPU and 8-GPU system analysis
- Thermal resistance breakdown
- Flow rate optimization for multi-GPU servers

**How to run:**
```bash
python examples/validation_nvidia_h100.py
```

**Expected output:**
- Junction temperatures matching published NVIDIA specifications
- Thermal resistance breakdown showing model accuracy
- Optimized cooling solution for 8-GPU AI training server

**Why this matters:**
This example proves the thermal model is based on validated physics, not arbitrary parameters. It demonstrates that this tool produces credible results for real-world GPU cooling design.

---

## Future Examples (Planned)

### Phase 2: Comparative Study
**File**: `comparative_cooling_analysis.py`
- Compare water vs immersion cooling for AI training clusters
- Professional trade-off analysis (thermal, cost, reliability)
- Real engineering decision-making workflow

### Phase 3: Complete Design Workflow
**File**: `design_datacenter_cooling.py`
- End-to-end: Given constraints (power, space, budget), design optimal cooling
- Iterative AI-human collaboration
- Shows how Claude Code assists thermal architecture design

---

## Data Sources

**NVIDIA H100 Specifications:**
- [H100 Tensor Core GPU Architecture White Paper](https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/h100/h100-datasheet.pdf)
- TDP: 700W
- Max Junction Temperature: 85°C
- Cooling: Liquid cold plate required

**Thermal Engineering References:**
- Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer"
- IEEE SEMI-THERM conference proceedings
- ASHRAE TC 9.9 Mission Critical Facilities
