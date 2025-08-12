# Novel Engine Evaluation Seeds
## Comprehensive Testing Scenarios for Iron Laws and Core Systems

This directory contains evaluation seed scenarios designed to comprehensively test the Novel Engine's Iron Laws validation system, decision-making capabilities, and core functionality.

## Seed Overview

### Seed 001: Basic Investigation (`seed_001_basic_investigation.yaml`)
- **Complexity**: Low
- **Focus**: Fundamental investigation mechanics and all 5 Iron Laws
- **Estimated Turns**: 5
- **Key Features**:
  - Basic action execution and resource management
  - Investigation mechanics validation
  - Iron Laws compliance baseline testing
  - Simple decision-making scenarios

### Seed 002: Resource Stress Test (`seed_002_resource_stress_test.yaml`)
- **Complexity**: Medium
- **Focus**: E002 Resource Law and constraint management
- **Estimated Turns**: 8
- **Key Features**:
  - Resource conservation under pressure
  - Decision optimization with limited resources
  - Emergency response scenarios
  - Risk/reward assessment testing

### Seed 003: Narrative Coherence (`seed_003_narrative_coherence.yaml`)
- **Complexity**: Medium  
- **Focus**: E004 Narrative Law and story consistency
- **Estimated Turns**: 10
- **Key Features**:
  - Character behavior consistency
  - Moral dilemma navigation
  - Relationship dynamics
  - Contextual appropriateness

### Seed 004: Social Hierarchy (`seed_004_social_hierarchy.yaml`)
- **Complexity**: High
- **Focus**: E005 Social Law and authority relationships
- **Estimated Turns**: 12
- **Key Features**:
  - Military hierarchy navigation
  - Authority relationship management
  - Protocol compliance
  - Leadership demonstration

### Seed 005: Physics & Causality (`seed_005_physics_causality.yaml`)
- **Complexity**: High
- **Focus**: E001 Causality Law and E003 Physics Law integration
- **Estimated Turns**: 15
- **Key Features**:
  - Complex system interactions
  - Logical action sequencing
  - Physical constraint handling
  - Multi-system dependencies

## Testing Coverage Matrix

| Iron Law | Seed 001 | Seed 002 | Seed 003 | Seed 004 | Seed 005 |
|----------|----------|----------|----------|----------|----------|
| E001 Causality | ✅ Basic | ⚪ Light | ⚪ Light | ⚪ Light | 🎯 **Primary** |
| E002 Resources | ✅ Basic | 🎯 **Primary** | ⚪ Light | ⚪ Light | ⚪ Light |
| E003 Physics | ✅ Basic | ⚪ Light | ⚪ Light | ⚪ Light | 🎯 **Primary** |
| E004 Narrative | ✅ Basic | ⚪ Light | 🎯 **Primary** | ⚪ Light | ⚪ Light |
| E005 Social | ✅ Basic | ⚪ Light | ⚪ Light | 🎯 **Primary** | ⚪ Light |

## Evaluation Categories

### Functional Testing
- **Basic Mechanics** (Seed 001): Core system functionality
- **Stress Testing** (Seed 002): Performance under constraints
- **Integration Testing** (Seeds 003-005): Complex scenario handling

### Iron Laws Validation
- **Individual Law Focus**: Each seed emphasizes 1-2 specific laws
- **Cross-Law Interaction**: Testing law interactions and conflicts
- **Repair System Testing**: Automatic violation repair mechanisms

### Decision Quality Assessment
- **Logical Consistency**: Causality and reasoning chains
- **Resource Optimization**: Efficiency and conservation
- **Social Appropriateness**: Context-sensitive behavior
- **Narrative Coherence**: Story and character consistency

## Usage Instructions

### Running Individual Seeds
```bash
# Run specific evaluation seed
python evaluate_baseline.py --seed evaluation/seeds/seed_001_basic_investigation.yaml

# Run with detailed output
python evaluate_baseline.py --seed evaluation/seeds/seed_002_resource_stress_test.yaml --verbose --save-detailed
```

### Running Complete Test Suite
```bash
# Run all seeds in sequence
python evaluate_baseline.py --suite evaluation/seeds/

# Run with performance metrics
python evaluate_baseline.py --suite evaluation/seeds/ --metrics --benchmark
```

### Batch Evaluation
```bash
# Run multiple iterations for statistical analysis
python evaluate_baseline.py --batch --iterations 10 --seeds evaluation/seeds/
```

## Output and Reporting

### Generated Reports
- **Individual Seed Reports**: Detailed analysis per scenario
- **Comparative Analysis**: Cross-seed performance comparison
- **Iron Laws Compliance Summary**: Law-specific validation results
- **Performance Metrics**: Execution time and resource usage

### Output Locations
```
evaluation/results/
├── seed_001/          # Basic investigation results
├── seed_002/          # Resource stress test results  
├── seed_003/          # Narrative coherence results
├── seed_004/          # Social hierarchy results
├── seed_005/          # Physics causality results
├── summary/           # Cross-seed analysis
└── benchmarks/        # Performance comparisons
```

## Seed File Format

Each seed file follows a standardized YAML structure:

```yaml
metadata:
  seed_id: "unique_identifier"
  complexity: "low|medium|high"
  evaluation_focus: ["law1", "law2", "feature"]

world_state:
  setting: "Scenario description"
  environment: {...}
  locations: [{...}]
  objects: [{...}]

characters:
  - character_id: "agent_id"
    # Character configuration

objectives:
  primary: [{...}]    # Must-complete objectives
  secondary: [{...}]  # Optional objectives

evaluation:
  metrics: {...}      # Success measurement criteria
  pass_thresholds: {...}  # Minimum requirements
```

## Customization and Extension

### Creating New Seeds
1. Copy an existing seed file as template
2. Modify world state, characters, and objectives
3. Update evaluation criteria and success metrics
4. Test seed validity with validation tools

### Seed Validation
```bash
# Validate seed file structure
python validate_seed.py evaluation/seeds/your_seed.yaml

# Test seed execution without full evaluation  
python test_seed.py evaluation/seeds/your_seed.yaml --dry-run
```

## Performance Benchmarks

### Expected Execution Times
- **Seed 001**: ~2-3 minutes (5 turns)
- **Seed 002**: ~4-5 minutes (8 turns) 
- **Seed 003**: ~5-7 minutes (10 turns)
- **Seed 004**: ~8-10 minutes (12 turns)
- **Seed 005**: ~10-15 minutes (15 turns)

### System Requirements
- **Minimum**: 4GB RAM, 2 CPU cores
- **Recommended**: 8GB RAM, 4 CPU cores
- **Storage**: 1GB for complete evaluation suite results

## Quality Assurance

### Seed Review Process
1. **Technical Review**: YAML validity, completeness
2. **Balance Review**: Appropriate difficulty progression
3. **Coverage Review**: Iron Laws and feature coverage
4. **Performance Review**: Execution time and resource usage

### Continuous Integration
- Automated seed validation on commits
- Performance regression testing
- Iron Laws compliance verification
- Cross-platform compatibility testing

---

**Note**: These evaluation seeds are designed to work with Novel Engine v1.0.0 and require the complete Iron Laws validation system to be implemented.