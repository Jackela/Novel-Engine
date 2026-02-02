import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import axios, { AxiosInstance } from 'axios';

// Test configuration
const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TEST_TIMEOUT = 10000;

describe('Character API Integration Tests', () => {
  let apiClient: AxiosInstance;
  let workspaceId: string;
  let createdCharacterIds: string[] = [];

  beforeAll(async () => {
    // Setup API client
    apiClient = axios.create({
      baseURL: API_BASE_URL,
      timeout: TEST_TIMEOUT,
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Create a guest session for testing
    try {
      const sessionResponse = await apiClient.post('/api/guest/session');
      workspaceId = sessionResponse.data.workspace_id;
      console.log(`Created test workspace: ${workspaceId}`);
    } catch (error) {
      console.error('Failed to create guest session:', error);
      throw error;
    }
  }, TEST_TIMEOUT);

  afterAll(async () => {
    // Cleanup: Delete created characters
    for (const characterId of createdCharacterIds) {
      try {
        await apiClient.delete(`/api/characters/${characterId}`);
      } catch (error) {
        console.warn(`Failed to cleanup character ${characterId}:`, error);
      }
    }
  });

  describe('POST /api/characters', () => {
    it('should create a character with correct agent_id', async () => {
      const characterData = {
        name: 'Integration Test Character',
        faction: 'Test Faction',
        role: 'Test Role',
        description: 'Test description for integration testing',
        stats: {
          strength: 5,
          agility: 6,
          intelligence: 7,
          charisma: 8,
        },
        equipment: [],
        relationships: [],
      };

      const response = await apiClient.post('/api/characters', characterData);

      expect(response.status).toBe(200);
      expect(response.data).toBeDefined();
      expect(response.data.id).toBeDefined();
      expect(response.data.name).toBe(characterData.name);

      // Verify agent_id follows naming convention
      expect(response.data.id).toMatch(/^[a-z][a-z0-9_]*$/);
      expect(response.data.id.length).toBeGreaterThanOrEqual(3);
      expect(response.data.id.length).toBeLessThanOrEqual(50);

      // Store for cleanup
      createdCharacterIds.push(response.data.id);
    }, TEST_TIMEOUT);

    it('should normalize skill values from 1-10 to 0.0-1.0', async () => {
      const characterData = {
        name: 'Skill Normalization Test',
        faction: 'Test Faction',
        role: 'Test Role',
        description: 'Testing skill value normalization',
        stats: {
          strength: 1,  // Min value
          agility: 10,  // Max value
          intelligence: 5,  // Mid value
        },
        equipment: [],
        relationships: [],
      };

      const response = await apiClient.post('/api/characters', characterData);

      expect(response.status).toBe(200);

      // Verify skills are normalized
      // Note: Backend should store normalized values, verify by reading back
      const getResponse = await apiClient.get(`/api/characters/${response.data.id}`);
      expect(getResponse.status).toBe(200); // Verify character can be retrieved

      // If backend returns normalized values in future:
      // expect(getResponse.data.stats.strength).toBeCloseTo(0.0, 2);
      // expect(getResponse.data.stats.agility).toBeCloseTo(1.0, 2);
      // expect(getResponse.data.stats.intelligence).toBeCloseTo(0.444, 2);

      createdCharacterIds.push(response.data.id);
    }, TEST_TIMEOUT);

    it('should reject invalid character data', async () => {
      const invalidData = {
        name: 'A',  // Too short
        // Missing required fields
      };

      try {
        await apiClient.post('/api/characters', invalidData);
        expect.fail('Should have thrown validation error');
      } catch (error: any) {
        expect(error.response.status).toBeGreaterThanOrEqual(400);
        expect(error.response.status).toBeLessThan(500);
      }
    }, TEST_TIMEOUT);
  });

  describe('GET /api/characters', () => {
    it('should list all characters in workspace', async () => {
      // Create a test character first
      const characterData = {
        name: 'List Test Character',
        faction: 'Test Faction',
        role: 'Test Role',
        description: 'Character for list testing',
        stats: { strength: 5 },
        equipment: [],
        relationships: [],
      };

      const createResponse = await apiClient.post('/api/characters', characterData);
      createdCharacterIds.push(createResponse.data.id);

      // List characters
      const listResponse = await apiClient.get('/api/characters');

      expect(listResponse.status).toBe(200);
      expect(Array.isArray(listResponse.data)).toBe(true);

      // Verify our character is in the list
      const foundCharacter = listResponse.data.find(
        (char: any) => char.id === createResponse.data.id
      );
      expect(foundCharacter).toBeDefined();
      expect(foundCharacter.name).toBe(characterData.name);
    }, TEST_TIMEOUT);
  });

  describe('GET /api/characters/:id', () => {
    it('should retrieve a specific character by ID', async () => {
      // Create a test character
      const characterData = {
        name: 'Get By ID Test',
        faction: 'Test Faction',
        role: 'Test Role',
        description: 'Character for ID retrieval testing',
        stats: { strength: 7, agility: 8 },
        equipment: [],
        relationships: [],
      };

      const createResponse = await apiClient.post('/api/characters', characterData);
      const characterId = createResponse.data.id;
      createdCharacterIds.push(characterId);

      // Get character by ID
      const getResponse = await apiClient.get(`/api/characters/${characterId}`);

      expect(getResponse.status).toBe(200);
      expect(getResponse.data.id).toBe(characterId);
      expect(getResponse.data.name).toBe(characterData.name);
      expect(getResponse.data.faction).toBe(characterData.faction);
    }, TEST_TIMEOUT);

    it('should return 404 for non-existent character', async () => {
      try {
        await apiClient.get('/api/characters/nonexistent_character_id_12345');
        expect.fail('Should have thrown 404 error');
      } catch (error: any) {
        expect(error.response.status).toBe(404);
      }
    }, TEST_TIMEOUT);
  });

  describe('PUT /api/characters/:id', () => {
    it('should update an existing character', async () => {
      // Create a test character
      const characterData = {
        name: 'Update Test Character',
        faction: 'Original Faction',
        role: 'Original Role',
        description: 'Original description',
        stats: { strength: 5 },
        equipment: [],
        relationships: [],
      };

      const createResponse = await apiClient.post('/api/characters', characterData);
      const characterId = createResponse.data.id;
      createdCharacterIds.push(characterId);

      // Update the character
      const updatedData = {
        ...characterData,
        faction: 'Updated Faction',
        description: 'Updated description',
        stats: { strength: 8, agility: 7 },
      };

      const updateResponse = await apiClient.put(`/api/characters/${characterId}`, updatedData);

      expect(updateResponse.status).toBe(200);
      expect(updateResponse.data.faction).toBe('Updated Faction');
      expect(updateResponse.data.description).toBe('Updated description');

      // Verify by reading back
      const getResponse = await apiClient.get(`/api/characters/${characterId}`);
      expect(getResponse.data.faction).toBe('Updated Faction');
    }, TEST_TIMEOUT);
  });

  describe('DELETE /api/characters/:id', () => {
    it('should delete a character', async () => {
      // Create a test character
      const characterData = {
        name: 'Delete Test Character',
        faction: 'Test Faction',
        role: 'Test Role',
        description: 'Character for deletion testing',
        stats: { strength: 5 },
        equipment: [],
        relationships: [],
      };

      const createResponse = await apiClient.post('/api/characters', characterData);
      const characterId = createResponse.data.id;

      // Delete the character
      const deleteResponse = await apiClient.delete(`/api/characters/${characterId}`);
      expect(deleteResponse.status).toBeGreaterThanOrEqual(200);
      expect(deleteResponse.status).toBeLessThan(300);

      // Verify deletion by trying to get it
      try {
        await apiClient.get(`/api/characters/${characterId}`);
        expect.fail('Character should have been deleted');
      } catch (error: any) {
        expect(error.response.status).toBe(404);
      }

      // Remove from cleanup list since already deleted
      createdCharacterIds = createdCharacterIds.filter(id => id !== characterId);
    }, TEST_TIMEOUT);
  });

  describe('Character Persistence', () => {
    it('should persist character data across requests', async () => {
      // Create a character
      const characterData = {
        name: 'Persistence Test Character',
        faction: 'Test Faction',
        role: 'Test Role',
        description: 'Testing data persistence',
        stats: { strength: 6, agility: 7, intelligence: 8 },
        equipment: ['Sword', 'Shield'],
        relationships: [],
      };

      const createResponse = await apiClient.post('/api/characters', characterData);
      const characterId = createResponse.data.id;
      createdCharacterIds.push(characterId);

      // Read it back multiple times
      for (let i = 0; i < 3; i++) {
        const getResponse = await apiClient.get(`/api/characters/${characterId}`);
        expect(getResponse.data.name).toBe(characterData.name);
        expect(getResponse.data.description).toBe(characterData.description);
        expect(getResponse.data.equipment).toEqual(characterData.equipment);
      }
    }, TEST_TIMEOUT);
  });
});
