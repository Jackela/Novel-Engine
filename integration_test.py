#!/usr/bin/env python3
"""System Integration Test for Multi-Agent Waves"""

# System Integration Test: Check cross-wave dependencies
print('=== SYSTEM INTEGRATION TEST ===')

wave_files = {
    'Wave 2': 'enhanced_multi_agent_bridge.py',
    'Wave 3': 'parallel_agent_coordinator.py', 
    'Wave 4': 'emergent_narrative_orchestrator.py',
    'Wave 5': 'enterprise_multi_agent_orchestrator.py'
}

# Test 1: Cross-file imports and dependencies
print('🔗 Cross-Wave Dependencies:')
dependencies = {}

for wave, filename in wave_files.items():
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    deps = []
    for other_wave, other_file in wave_files.items():
        if other_wave != wave:
            module_name = other_file.replace('.py', '')
            if module_name in content or other_file in content:
                deps.append(other_wave)
    
    dependencies[wave] = deps
    print(f'   {wave}: depends on {deps if deps else "[none]"}')

# Test 2: Event Bus integration
print('\n📡 Event Bus Integration:')
for wave, filename in wave_files.items():
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    event_features = []
    if 'event_bus' in content.lower():
        event_features.append('EventBus parameter')
    if 'subscribe' in content:
        event_features.append('Event subscription')
    if 'emit' in content:
        event_features.append('Event emission')
    
    status = '✅' if event_features else '⚠️ '
    print(f'   {status} {wave}: {event_features if event_features else "No event integration"}')

print('\n🎯 Integration Assessment:')
total_dependencies = sum(len(deps) for deps in dependencies.values())
print(f'   Total cross-wave dependencies: {total_dependencies}')
print(f'   Dependency density: {total_dependencies / len(wave_files):.1f} per wave')

if total_dependencies >= 3:
    print('✅ Good integration between waves detected')
else:
    print('⚠️  Lower integration - may need review')