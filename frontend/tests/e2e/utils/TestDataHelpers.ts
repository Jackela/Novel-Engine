/**
 * Test Data Helpers for Emergent Narrative Dashboard UAT
 * 
 * Provides utilities for:
 * - Mock data generation
 * - Test scenario setup
 * - API response validation
 * - Performance benchmarking
 */

export interface TestCharacter {
  id: string;
  name: string;
  type: 'protagonist' | 'npc' | 'antagonist';
  status: 'active' | 'inactive' | 'pending';
  position: { x: number; y: number; z: number };
  activity: number; // 0.0 to 1.0
  relationships?: string[];
}

export interface TestNarrativeArc {
  id: string;
  name: string;
  status: 'active' | 'completed' | 'paused';
  completion: number; // 0.0 to 1.0
  participants: string[];
  events: string[];
  priority: 'high' | 'medium' | 'low';
}

export interface TestCampaign {
  id: string;
  name: string;
  currentTurn: number;
  totalTurns: number;
  status: 'active' | 'paused' | 'completed';
  startTime: string;
  lastUpdate: string;
}

export interface TestOrchestrationState {
  phase: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  startTime: string;
  duration?: number;
  progress: number; // 0.0 to 1.0
}

/**
 * Generate comprehensive test data set for dashboard UAT
 */
export class TestDataGenerator {
  /**
   * Generate test characters with realistic data patterns
   */
  static generateTestCharacters(count: number = 5): TestCharacter[] {
    const names = [
      'Aria Shadowbane', 'Merchant Aldric', 'Elder Thorne', 'Captain Vera', 
      'Mage Lysander', 'Rogue Kira', 'Blacksmith Gareth', 'Priestess Elena'
    ];
    
    const types: TestCharacter['type'][] = ['protagonist', 'npc', 'antagonist'];
    
    return Array.from({ length: count }, (_, index) => ({
      id: `char-${(index + 1).toString().padStart(3, '0')}`,
      name: names[index] || `Character ${index + 1}`,
      type: types[index % types.length],
      status: 'active',
      position: {
        x: 50 + (Math.random() * 200),
        y: 50 + (Math.random() * 200), 
        z: Math.random() * 10
      },
      activity: Math.random(),
      relationships: index > 0 ? [`char-${Math.max(1, index).toString().padStart(3, '0')}`] : []
    }));
  }
  
  /**
   * Generate test narrative arcs with character connections
   */
  static generateTestArcs(characters: TestCharacter[], count: number = 3): TestNarrativeArc[] {
    const arcTemplates = [
      'The Ancient Prophecy',
      'Merchant Relations', 
      'Political Intrigue',
      'The Lost Artifact',
      'Border Conflicts'
    ];
    
    return Array.from({ length: count }, (_, index) => ({
      id: `arc-${(index + 1).toString().padStart(3, '0')}`,
      name: arcTemplates[index] || `Arc ${index + 1}`,
      status: 'active',
      completion: Math.random() * 0.8, // 0-80% completion for active arcs
      participants: characters
        .slice(0, Math.min(3, characters.length))
        .map(char => char.id),
      events: [
        `event-${index * 3 + 1}`,
        `event-${index * 3 + 2}`, 
        `event-${index * 3 + 3}`
      ],
      priority: ['high', 'medium', 'low'][index % 3] as TestNarrativeArc['priority']
    }));
  }
  
  /**
   * Generate test campaign data
   */
  static generateTestCampaign(): TestCampaign {
    const now = new Date();
    const startTime = new Date(now.getTime() - (7 * 24 * 60 * 60 * 1000)); // 7 days ago
    
    return {
      id: 'campaign-001',
      name: 'UAT Test Campaign',
      currentTurn: 42,
      totalTurns: 150,
      status: 'active',
      startTime: startTime.toISOString(),
      lastUpdate: now.toISOString()
    };
  }
  
  /**
   * Generate turn orchestration pipeline states
   */
  static generateOrchestrationStates(): TestOrchestrationState[] {
    const phases = [
      'World Update',
      'Subjective Brief',
      'Interaction Orchestration', 
      'Event Integration',
      'Narrative Integration'
    ];
    
    return phases.map((phase, index) => ({
      phase,
      status: index < 2 ? 'completed' : index === 2 ? 'processing' : 'pending',
      startTime: new Date(Date.now() - (5 - index) * 1000).toISOString(),
      duration: index < 2 ? 2000 + Math.random() * 3000 : undefined,
      progress: index < 2 ? 1.0 : index === 2 ? 0.6 : 0.0
    }));
  }
}

/**
 * API Response Validator for UAT
 */
export class APIResponseValidator {
  /**
   * Validate character data structure matches OpenAPI spec
   */
  static validateCharacterResponse(data: any): boolean {
    return (
      data &&
      typeof data.id === 'string' &&
      typeof data.name === 'string' &&
      ['protagonist', 'npc', 'antagonist'].includes(data.type) &&
      ['active', 'inactive', 'pending'].includes(data.status) &&
      data.position &&
      typeof data.position.x === 'number' &&
      typeof data.position.y === 'number' &&
      typeof data.activity === 'number' &&
      data.activity >= 0 && data.activity <= 1
    );
  }
  
  /**
   * Validate narrative arc response structure
   */
  static validateArcResponse(data: any): boolean {
    return (
      data &&
      typeof data.id === 'string' &&
      typeof data.name === 'string' &&
      ['active', 'completed', 'paused'].includes(data.status) &&
      typeof data.completion === 'number' &&
      data.completion >= 0 && data.completion <= 1 &&
      Array.isArray(data.participants)
    );
  }
  
  /**
   * Validate turn orchestration response
   */
  static validateOrchestrationResponse(data: any): boolean {
    return (
      data &&
      typeof data.turnId === 'string' &&
      ['initiated', 'processing', 'completed', 'failed'].includes(data.status) &&
      Array.isArray(data.phases) &&
      data.phases.length === 5
    );
  }
}

/**
 * Performance Benchmarking Utilities
 */
export class PerformanceBenchmark {
  private static benchmarks: Map<string, number[]> = new Map();
  
  /**
   * Record performance measurement
   */
  static record(operation: string, duration: number): void {
    if (!this.benchmarks.has(operation)) {
      this.benchmarks.set(operation, []);
    }
    this.benchmarks.get(operation)!.push(duration);
  }
  
  /**
   * Get performance statistics for operation
   */
  static getStats(operation: string): {
    count: number;
    average: number;
    min: number;
    max: number;
    p95: number;
  } | null {
    const measurements = this.benchmarks.get(operation);
    if (!measurements || measurements.length === 0) return null;
    
    const sorted = [...measurements].sort((a, b) => a - b);
    const sum = measurements.reduce((a, b) => a + b, 0);
    
    return {
      count: measurements.length,
      average: sum / measurements.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      p95: sorted[Math.floor(sorted.length * 0.95)]
    };
  }
  
  /**
   * Clear all benchmarks
   */
  static clear(): void {
    this.benchmarks.clear();
  }
  
  /**
   * Generate performance report
   */
  static generateReport(): Record<string, any> {
    const report: Record<string, any> = {};
    
    for (const [operation] of this.benchmarks.entries()) {
      report[operation] = this.getStats(operation);
    }
    
    return report;
  }
}

/**
 * UAT Validation Helpers
 */
export class UATValidationHelpers {
  /**
   * Validate dashboard component visibility requirements
   */
  static async validateComponentVisibility(
    components: Record<string, boolean>
  ): Promise<{ passed: number; failed: number; issues: string[] }> {
    let passed = 0;
    let failed = 0;
    const issues: string[] = [];
    
    for (const [component, isVisible] of Object.entries(components)) {
      if (isVisible) {
        passed++;
      } else {
        failed++;
        issues.push(`Component "${component}" is not visible`);
      }
    }
    
    return { passed, failed, issues };
  }
  
  /**
   * Validate layout positioning meets requirements
   */
  static validateLayoutPositioning(
    layoutData: Record<string, boolean>
  ): { compliant: boolean; issues: string[] } {
    const issues: string[] = [];
    let compliant = true;
    
    for (const [component, isCorrect] of Object.entries(layoutData)) {
      if (!isCorrect) {
        compliant = false;
        issues.push(`Component "${component}" has incorrect grid positioning`);
      }
    }
    
    return { compliant, issues };
  }
  
  /**
   * Validate performance against benchmarks
   */
  static validatePerformance(
    measurements: Record<string, number>,
    thresholds: Record<string, number>
  ): { passed: boolean; issues: string[] } {
    const issues: string[] = [];
    let passed = true;
    
    for (const [metric, value] of Object.entries(measurements)) {
      const threshold = thresholds[metric];
      if (threshold && value > threshold) {
        passed = false;
        issues.push(`Performance metric "${metric}" (${value}ms) exceeds threshold (${threshold}ms)`);
      }
    }
    
    return { passed, issues };
  }
}
