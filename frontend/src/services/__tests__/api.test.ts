import { describe, it, expect } from 'vitest';
import { generateAgentId, normalizeSkillValue } from '../api';

describe('generateAgentId', () => {
  it('should convert name to lowercase with underscores', () => {
    expect(generateAgentId('Test Agent')).toBe('test_agent');
    expect(generateAgentId('John Doe')).toBe('john_doe');
    expect(generateAgentId('Agent 007')).toBe('agent_007');
  });

  it('should handle names with multiple spaces', () => {
    expect(generateAgentId('Test   Agent   Name')).toBe('test_agent_name');
  });

  it('should handle names starting with numbers', () => {
    const result = generateAgentId('123 Agent');
    expect(result).toBe('agent_123_agent');
  });

  it('should remove special characters', () => {
    expect(generateAgentId('Test@Agent#123')).toBe('testagent123');
  });

  it('should enforce minimum length of 3 characters', () => {
    const result = generateAgentId('A');
    expect(result.length).toBeGreaterThanOrEqual(3);
  });

  it('should enforce maximum length of 50 characters', () => {
    const longName = 'A'.repeat(100);
    const result = generateAgentId(longName);
    expect(result.length).toBeLessThanOrEqual(50);
  });

  it('should handle empty string', () => {
    const result = generateAgentId('');
    expect(result.length).toBeGreaterThanOrEqual(3);
  });

  it('should be idempotent (same input produces same output)', () => {
    const name = 'Test Agent';
    const result1 = generateAgentId(name);
    const result2 = generateAgentId(name);
    expect(result1).toBe(result2);
  });
});

describe('normalizeSkillValue', () => {
  it('should convert 1-10 range to 0.0-1.0', () => {
    expect(normalizeSkillValue(1)).toBeCloseTo(0.0, 2);
    expect(normalizeSkillValue(5)).toBeCloseTo(0.444, 2);
    expect(normalizeSkillValue(10)).toBeCloseTo(1.0, 2);
  });

  it('should handle boundary values', () => {
    expect(normalizeSkillValue(1)).toBe(0.0);
    expect(normalizeSkillValue(10)).toBe(1.0);
  });

  it('should clamp values below minimum', () => {
    expect(normalizeSkillValue(0)).toBe(0.0);
    expect(normalizeSkillValue(-5)).toBe(0.0);
  });

  it('should clamp values above maximum', () => {
    expect(normalizeSkillValue(11)).toBe(1.0);
    expect(normalizeSkillValue(100)).toBe(1.0);
  });

  it('should handle decimal inputs', () => {
    expect(normalizeSkillValue(5.5)).toBeCloseTo(0.5, 1);
  });

  it('should handle mid-range values correctly', () => {
    expect(normalizeSkillValue(2)).toBeCloseTo(0.111, 2);
    expect(normalizeSkillValue(6)).toBeCloseTo(0.555, 2);
    expect(normalizeSkillValue(9)).toBeCloseTo(0.888, 2);
  });

  it('should always return a number between 0 and 1', () => {
    const testValues = [-10, 0, 1, 5, 10, 15, 100];
    testValues.forEach(value => {
      const result = normalizeSkillValue(value);
      expect(result).toBeGreaterThanOrEqual(0);
      expect(result).toBeLessThanOrEqual(1);
    });
  });
});
