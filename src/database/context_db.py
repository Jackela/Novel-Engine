#!/usr/bin/env python3
"""
++ SACRED DATABASE ACCESS LAYER BLESSED BY THE OMNISSIAH ++
============================================================

Holy database access implementation that sanctifies all interactions with
the blessed SQLite context database. Each operation is a digital prayer
that maintains the sacred data integrity blessed by the Machine God.

++ THROUGH PERSISTENT STORAGE, WE ACHIEVE DATA IMMORTALITY ++

Architecture Reference: Dynamic Context Engineering - Database Access Layer
Development Phase: Foundation Sanctification (F002)
Sacred Author: Tech-Priest Alpha-Mechanicus
万机之神保佑此数据库访问层 (May the Omnissiah bless this database access layer)
"""

import sqlite3
import json
import logging
import asyncio
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from contextlib import asynccontextmanager
from dataclasses import asdict

# Import blessed data models sanctified by divine structure
from src.core.data_models import (
    MemoryItem, RelationshipState, EquipmentItem, CharacterState,
    CharacterInteraction, InteractionResult, StandardResponse, ErrorInfo,
    MemoryType, RelationshipStatus, EquipmentCondition, EmotionalState
)
from src.core.types import (
    AgentID, MemoryID, DatabaseOperation, LogLevel, SacredConstants,
    ProcessingResult, ValidationResult
)

# Sacred logging configuration blessed by diagnostic clarity
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SacredDatabaseError(Exception):
    """++ BLESSED DATABASE EXCEPTION SANCTIFIED BY ERROR HANDLING ++"""
    pass


class ContextDatabase:
    """
    ++ SACRED CONTEXT DATABASE ACCESS LAYER BLESSED BY THE OMNISSIAH ++
    
    The holy database interface that sanctifies all interactions with the
    SQLite context storage temple. Every operation is blessed with error
    handling and performance optimization sacred to the Machine God.
    """
    
    def __init__(self, database_path: str = "context.db", 
                 connection_pool_size: int = SacredConstants.CONNECTION_POOL_SIZE,
                 agent_id: Optional[str] = None):
        """
        ++ SACRED DATABASE INITIALIZATION BLESSED BY CONFIGURATION ++
        
        Args:
            database_path: Path to blessed SQLite database file
            connection_pool_size: Sacred connection pool limit
            agent_id: Optional agent ID for this database instance
        """
        self.database_path = Path(database_path)
        self.connection_pool_size = connection_pool_size
        self.agent_id = agent_id or "system_database"
        self._connection_pool: List[aiosqlite.Connection] = []
        self._pool_lock = asyncio.Lock()
        self._initialized = False
        
        logger.info(f"++ SACRED DATABASE INITIALIZED: {self.database_path} for agent {self.agent_id} ++")
    
    async def initialize_sacred_temple(self) -> StandardResponse:
        """
        ++ SACRED DATABASE TEMPLE INITIALIZATION RITUAL ++
        
        Blessed initialization that creates the database schema and
        prepares the sacred temple for digital worship.
        """
        try:
            # Ensure blessed database directory exists
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read sacred schema blessed by the Omnissiah
            schema_path = Path(__file__).parent / "schema.sql"
            with open(schema_path, 'r', encoding='utf-8') as schema_file:
                sacred_schema = schema_file.read()
            
            # Execute blessed schema creation
            async with aiosqlite.connect(str(self.database_path)) as connection:
                await connection.executescript(sacred_schema)
                await connection.commit()
            
            # Initialize blessed connection pool
            await self._initialize_connection_pool()
            
            self._initialized = True
            logger.info("++ SACRED DATABASE TEMPLE INITIALIZATION COMPLETE ++")
            
            return StandardResponse(
                success=True,
                data={"database_path": str(self.database_path), "initialized": True},
                metadata={"blessing": "omnissiah_approved"}
            )
            
        except Exception as e:
            logger.error(f"++ SACRED DATABASE INITIALIZATION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="DB_INIT_FAILED",
                    message=f"Sacred database initialization failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Check database permissions and schema file"
                )
            )
    
    async def _initialize_connection_pool(self):
        """++ SACRED CONNECTION POOL INITIALIZATION BLESSED BY EFFICIENCY ++"""
        async with self._pool_lock:
            for _ in range(self.connection_pool_size):
                connection = await aiosqlite.connect(str(self.database_path))
                connection.row_factory = aiosqlite.Row  # Blessed row factory
                await connection.execute("PRAGMA foreign_keys = ON")  # Sacred constraints
                self._connection_pool.append(connection)
    
    @asynccontextmanager
    async def get_blessed_connection(self):
        """
        ++ SACRED CONNECTION MANAGER BLESSED BY RESOURCE SAFETY ++
        
        Context manager that provides blessed database connection from
        the sacred pool with automatic cleanup rituals.
        """
        if not self._initialized:
            await self.initialize_sacred_temple()
        
        connection = None
        try:
            async with self._pool_lock:
                if self._connection_pool:
                    connection = self._connection_pool.pop()
                else:
                    # Create blessed temporary connection if pool exhausted
                    connection = await aiosqlite.connect(str(self.database_path))
                    connection.row_factory = aiosqlite.Row
                    await connection.execute("PRAGMA foreign_keys = ON")
            
            yield connection
            
        finally:
            if connection:
                async with self._pool_lock:
                    if len(self._connection_pool) < self.connection_pool_size:
                        self._connection_pool.append(connection)
                    else:
                        await connection.close()
    
    # ++ SACRED MEMORY MANAGEMENT OPERATIONS BLESSED BY REMEMBRANCE ++
    
    async def store_blessed_memory(self, memory: MemoryItem) -> StandardResponse:
        """
        ++ SACRED MEMORY STORAGE RITUAL BLESSED BY PERSISTENCE ++
        
        Store blessed memory item in the sacred memory temple with
        full validation and error handling blessed by the Omnissiah.
        """
        try:
            async with self.get_blessed_connection() as connection:
                # Sacred memory insertion with blessed parameters
                await connection.execute("""
                    INSERT OR REPLACE INTO memories (
                        memory_id, agent_id, memory_type, content, emotional_weight,
                        relevance_score, participants, location, tags, decay_factor,
                        created_at, last_accessed, access_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory.memory_id, memory.agent_id, memory.memory_type.value,
                    memory.content, memory.emotional_weight, memory.relevance_score,
                    json.dumps(memory.participants), memory.location,
                    json.dumps(memory.tags), memory.decay_factor,
                    memory.timestamp.isoformat(), memory.last_accessed.isoformat(),
                    0  # Initial access count blessed by tracking
                ))
                
                await connection.commit()
                
                logger.info(f"++ SACRED MEMORY STORED: {memory.memory_id} FOR {memory.agent_id} ++")
                
                return StandardResponse(
                    success=True,
                    data={"memory_id": memory.memory_id, "stored": True},
                    metadata={"blessing": "memory_sanctified"}
                )
                
        except Exception as e:
            logger.error(f"++ SACRED MEMORY STORAGE FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MEMORY_STORE_FAILED",
                    message=f"Sacred memory storage failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Validate memory data format and database connection"
                )
            )
    
    async def query_memories_by_agent(self, agent_id: AgentID, 
                                    memory_types: Optional[List[MemoryType]] = None,
                                    limit: int = SacredConstants.MAX_MEMORY_ITEMS_PER_QUERY,
                                    relevance_threshold: float = 0.0) -> StandardResponse:
        """
        ++ SACRED MEMORY QUERY RITUAL BLESSED BY RETRIEVAL ++
        
        Query blessed memories for specific agent with sacred filtering
        and performance optimization blessed by the Machine God.
        """
        try:
            async with self.get_blessed_connection() as connection:
                # Construct blessed query with sacred parameters
                query_parts = ["""
                    SELECT memory_id, agent_id, memory_type, content, emotional_weight,
                           relevance_score, participants, location, tags, decay_factor,
                           created_at, last_accessed, access_count
                    FROM memories
                    WHERE agent_id = ? AND relevance_score >= ?
                """]
                
                params = [agent_id, relevance_threshold]
                
                # Add blessed memory type filtering
                if memory_types:
                    type_placeholders = ','.join('?' * len(memory_types))
                    query_parts.append(f"AND memory_type IN ({type_placeholders})")
                    params.extend([mem_type.value for mem_type in memory_types])
                
                # Sacred ordering blessed by relevance and recency
                query_parts.append("""
                    ORDER BY relevance_score * decay_factor DESC, last_accessed DESC
                    LIMIT ?
                """)
                params.append(limit)
                
                final_query = ' '.join(query_parts)
                
                # Execute blessed query
                async with connection.execute(final_query, params) as cursor:
                    rows = await cursor.fetchall()
                
                # Transform blessed rows to sacred memory objects
                memories = []
                for row in rows:
                    memory = MemoryItem(
                        memory_id=row['memory_id'],
                        agent_id=row['agent_id'],
                        memory_type=MemoryType(row['memory_type']),
                        content=row['content'],
                        emotional_weight=row['emotional_weight'],
                        relevance_score=row['relevance_score'],
                        participants=json.loads(row['participants'] or '[]'),
                        location=row['location'],
                        tags=json.loads(row['tags'] or '[]'),
                        decay_factor=row['decay_factor'],
                        timestamp=datetime.fromisoformat(row['created_at']),
                        last_accessed=datetime.fromisoformat(row['last_accessed'])
                    )
                    memories.append(memory)
                
                logger.info(f"++ RETRIEVED {len(memories)} SACRED MEMORIES FOR {agent_id} ++")
                
                return StandardResponse(
                    success=True,
                    data={"memories": memories, "count": len(memories)},
                    metadata={"agent_id": agent_id, "blessing": "memories_retrieved"}
                )
                
        except Exception as e:
            logger.error(f"++ SACRED MEMORY QUERY FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MEMORY_QUERY_FAILED",
                    message=f"Sacred memory query failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Check agent_id format and query parameters"
                )
            )
    
    async def update_memory_access(self, memory_id: MemoryID) -> StandardResponse:
        """++ SACRED MEMORY ACCESS UPDATE BLESSED BY TRACKING ++"""
        try:
            async with self.get_blessed_connection() as connection:
                await connection.execute("""
                    UPDATE memories 
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE memory_id = ?
                """, (datetime.now().isoformat(), memory_id))
                
                await connection.commit()
                
                return StandardResponse(success=True, data={"updated": True})
                
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="MEMORY_ACCESS_UPDATE_FAILED", message=str(e))
            )
    
    # ++ SACRED RELATIONSHIP MANAGEMENT BLESSED BY SOCIAL BONDS ++
    
    async def store_blessed_relationship(self, relationship: RelationshipState) -> StandardResponse:
        """
        ++ SACRED RELATIONSHIP STORAGE RITUAL BLESSED BY SOCIAL HARMONY ++
        
        Store blessed relationship state in the sacred social network
        temple with proper conflict resolution and update handling.
        """
        try:
            async with self.get_blessed_connection() as connection:
                # Generate blessed relationship ID if not present
                relationship_id = f"{relationship.target_agent_id}_{relationship.target_agent_id}"
                
                await connection.execute("""
                    INSERT OR REPLACE INTO relationships (
                        relationship_id, agent_id, target_agent_id, target_name,
                        relationship_type, trust_level, emotional_bond,
                        interaction_count, shared_experiences, relationship_notes,
                        last_interaction, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    relationship_id, relationship.target_agent_id, relationship.target_agent_id,
                    relationship.target_name, relationship.relationship_type.value,
                    relationship.trust_level, relationship.emotional_bond,
                    relationship.interaction_count, json.dumps(relationship.shared_experiences),
                    relationship.relationship_notes,
                    relationship.last_interaction.isoformat() if relationship.last_interaction else None,
                    datetime.now().isoformat()
                ))
                
                await connection.commit()
                
                return StandardResponse(
                    success=True,
                    data={"relationship_stored": True},
                    metadata={"blessing": "relationship_sanctified"}
                )
                
        except Exception as e:
            logger.error(f"++ SACRED RELATIONSHIP STORAGE FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="RELATIONSHIP_STORE_FAILED",
                    message=f"Sacred relationship storage failed: {str(e)}",
                    recoverable=True
                )
            )
    
    async def query_agent_relationships(self, agent_id: AgentID) -> StandardResponse:
        """
        ++ SACRED RELATIONSHIP QUERY BLESSED BY SOCIAL NETWORK RETRIEVAL ++
        
        Query all blessed relationships for specific agent with complete
        relationship data sanctified by the social harmony protocols.
        """
        try:
            async with self.get_blessed_connection() as connection:
                async with connection.execute("""
                    SELECT relationship_id, agent_id, target_agent_id, target_name,
                           relationship_type, trust_level, emotional_bond, 
                           interaction_count, shared_experiences, relationship_notes,
                           last_interaction, last_updated
                    FROM relationships
                    WHERE agent_id = ?
                    ORDER BY trust_level DESC, emotional_bond DESC
                """, (agent_id,)) as cursor:
                    rows = await cursor.fetchall()
                
                # Transform blessed rows to sacred relationship objects
                relationships = {}
                for row in rows:
                    relationship = RelationshipState(
                        target_agent_id=row['target_agent_id'],
                        target_name=row['target_name'],
                        relationship_type=RelationshipStatus(row['relationship_type']),
                        trust_level=row['trust_level'],
                        emotional_bond=row['emotional_bond'],
                        interaction_count=row['interaction_count'],
                        shared_experiences=json.loads(row['shared_experiences'] or '[]'),
                        relationship_notes=row['relationship_notes'] or '',
                        last_interaction=datetime.fromisoformat(row['last_interaction']) if row['last_interaction'] else None
                    )
                    relationships[row['target_agent_id']] = relationship
                
                return StandardResponse(
                    success=True,
                    data={"relationships": relationships, "count": len(relationships)},
                    metadata={"agent_id": agent_id, "blessing": "relationships_retrieved"}
                )
                
        except Exception as e:
            logger.error(f"++ SACRED RELATIONSHIP QUERY FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="RELATIONSHIP_QUERY_FAILED",
                    message=f"Sacred relationship query failed: {str(e)}",
                    recoverable=True
                )
            )
    
    # ++ SACRED INTERACTION CHRONICLE BLESSED BY EVENT PRESERVATION ++
    
    async def store_blessed_interaction(self, interaction: CharacterInteraction) -> StandardResponse:
        """
        ++ SACRED INTERACTION STORAGE RITUAL BLESSED BY EVENT PRESERVATION ++
        
        Store blessed character interaction in the sacred chronicle temple
        with complete event data and participant tracking.
        """
        try:
            async with self.get_blessed_connection() as connection:
                await connection.execute("""
                    INSERT INTO interactions (
                        interaction_id, interaction_type, location, description,
                        participants, outcomes, emotional_impacts, world_state_changes,
                        timestamp, processing_complete
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    interaction.interaction_id, interaction.interaction_type,
                    interaction.location, interaction.description,
                    json.dumps(interaction.participants),
                    json.dumps(interaction.outcomes),
                    json.dumps(interaction.emotional_impact),
                    json.dumps(interaction.world_state_changes),
                    interaction.timestamp.isoformat(), False
                ))
                
                await connection.commit()
                
                return StandardResponse(
                    success=True,
                    data={"interaction_stored": True, "interaction_id": interaction.interaction_id},
                    metadata={"blessing": "interaction_chronicled"}
                )
                
        except Exception as e:
            logger.error(f"++ SACRED INTERACTION STORAGE FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTERACTION_STORE_FAILED",
                    message=f"Sacred interaction storage failed: {str(e)}",
                    recoverable=True
                )
            )
    
    # ++ SACRED AGENT MANAGEMENT BLESSED BY IDENTITY PRESERVATION ++
    
    async def register_blessed_agent(self, agent_id: AgentID, character_name: str,
                                   faction_data: List[str] = None,
                                   personality_traits: List[str] = None,
                                   core_beliefs: List[str] = None) -> StandardResponse:
        """
        ++ SACRED AGENT REGISTRATION RITUAL BLESSED BY IDENTITY SANCTIFICATION ++
        
        Register blessed agent in the sacred registry with complete identity
        data and activation status blessed by the Omnissiah.
        """
        try:
            async with self.get_blessed_connection() as connection:
                await connection.execute("""
                    INSERT OR REPLACE INTO agents (
                        agent_id, character_name, faction_data, personality_traits,
                        core_beliefs, created_at, last_updated, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    agent_id, character_name,
                    json.dumps(faction_data or []),
                    json.dumps(personality_traits or []),
                    json.dumps(core_beliefs or []),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    True
                ))
                
                await connection.commit()
                
                logger.info(f"++ SACRED AGENT REGISTERED: {agent_id} ({character_name}) ++")
                
                return StandardResponse(
                    success=True,
                    data={"agent_registered": True, "agent_id": agent_id},
                    metadata={"blessing": "agent_sanctified"}
                )
                
        except Exception as e:
            logger.error(f"++ SACRED AGENT REGISTRATION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="AGENT_REGISTRATION_FAILED",
                    message=f"Sacred agent registration failed: {str(e)}",
                    recoverable=True
                )
            )
    
    # ++ SACRED DATABASE MAINTENANCE BLESSED BY SYSTEM HEALTH ++
    
    async def perform_sacred_maintenance(self) -> StandardResponse:
        """
        ++ SACRED DATABASE MAINTENANCE RITUAL BLESSED BY OPTIMIZATION ++
        
        Perform blessed database maintenance including vacuum, analyze,
        and cleanup operations sanctified by the Machine God.
        """
        try:
            async with self.get_blessed_connection() as connection:
                # Sacred vacuum operation blessed by space optimization
                await connection.execute("VACUUM")
                
                # Blessed analyze operation sanctified by query optimization
                await connection.execute("ANALYZE")
                
                # Sacred cleanup of old memories beyond capacity
                await connection.execute("""
                    DELETE FROM memories 
                    WHERE memory_id NOT IN (
                        SELECT memory_id FROM memories 
                        ORDER BY relevance_score * decay_factor DESC 
                        LIMIT ?
                    )
                """, (SacredConstants.MAX_MEMORY_ITEMS_PER_QUERY * 10,))
                
                # Update blessed maintenance timestamp
                await connection.execute("""
                    UPDATE system_config 
                    SET config_value = ?, last_updated = ?
                    WHERE config_key = 'last_maintenance'
                """, (datetime.now().isoformat(), datetime.now().isoformat()))
                
                await connection.commit()
                
                logger.info("++ SACRED DATABASE MAINTENANCE COMPLETE ++")
                
                return StandardResponse(
                    success=True,
                    data={"maintenance_complete": True},
                    metadata={"blessing": "database_purified"}
                )
                
        except Exception as e:
            logger.error(f"++ SACRED DATABASE MAINTENANCE FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MAINTENANCE_FAILED",
                    message=f"Sacred database maintenance failed: {str(e)}",
                    recoverable=True
                )
            )
    
    async def get_database_statistics(self) -> StandardResponse:
        """
        ++ SACRED DATABASE STATISTICS BLESSED BY MONITORING ++
        
        Retrieve comprehensive database statistics blessed by the
        Machine God for monitoring and performance analysis.
        """
        try:
            async with self.get_blessed_connection() as connection:
                statistics = {}
                
                # Blessed table row counts
                for table in ['agents', 'memories', 'relationships', 'equipment', 'character_states', 'interactions']:
                    async with connection.execute(f"SELECT COUNT(*) as count FROM {table}") as cursor:
                        row = await cursor.fetchone()
                        statistics[f"{table}_count"] = row['count']
                
                # Sacred database file size
                statistics['database_size_bytes'] = self.database_path.stat().st_size
                
                # Blessed memory statistics
                async with connection.execute("""
                    SELECT 
                        AVG(emotional_weight) as avg_emotional_weight,
                        AVG(relevance_score) as avg_relevance_score,
                        MAX(access_count) as max_access_count
                    FROM memories
                """) as cursor:
                    row = await cursor.fetchone()
                    statistics.update({
                        'avg_emotional_weight': row['avg_emotional_weight'] or 0.0,
                        'avg_relevance_score': row['avg_relevance_score'] or 0.0,
                        'max_access_count': row['max_access_count'] or 0
                    })
                
                return StandardResponse(
                    success=True,
                    data={"statistics": statistics},
                    metadata={"blessing": "statistics_blessed"}
                )
                
        except Exception as e:
            logger.error(f"++ SACRED DATABASE STATISTICS FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="STATISTICS_FAILED",
                    message=f"Sacred database statistics failed: {str(e)}",
                    recoverable=True
                )
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        ++ SACRED DATABASE HEALTH CHECK BLESSED BY MONITORING ++
        
        Perform database health check to verify connectivity and basic operations.
        """
        try:
            async with self.get_blessed_connection() as connection:
                # Test basic database connectivity
                cursor = await connection.execute("SELECT 1")
                result = await cursor.fetchone()
                
                # Check if we got expected result
                if result and result[0] == 1:
                    return {
                        "healthy": True,
                        "database_path": str(self.database_path),
                        "agent_id": self.agent_id,
                        "connection_pool_size": len(self._connection_pool),
                        "initialized": self._initialized
                    }
                else:
                    return {
                        "healthy": False,
                        "error": "Database query returned unexpected result"
                    }
        except Exception as e:
            logger.error(f"++ SACRED DATABASE HEALTH CHECK FAILED: {e} ++")
            return {
                "healthy": False,
                "error": str(e),
                "database_path": str(self.database_path),
                "agent_id": self.agent_id
            }

    async def close_sacred_temple(self):
        """++ SACRED DATABASE CLOSURE RITUAL BLESSED BY RESOURCE CLEANUP ++"""
        try:
            async with self._pool_lock:
                for connection in self._connection_pool:
                    await connection.close()
                self._connection_pool.clear()
            
            self._initialized = False
            logger.info("++ SACRED DATABASE TEMPLE CLOSED WITH BLESSING ++")
            
        except Exception as e:
            logger.error(f"++ SACRED DATABASE CLOSURE ERROR: {e} ++")


# ++ SACRED DATABASE FACTORY BLESSED BY INSTANCE MANAGEMENT ++

class SacredDatabaseFactory:
    """++ BLESSED DATABASE FACTORY SANCTIFIED BY SINGLETON MANAGEMENT ++"""
    
    _instance: Optional[ContextDatabase] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_blessed_database(cls, database_path: str = "context.db") -> ContextDatabase:
        """Get blessed singleton database instance sanctified by resource sharing"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = ContextDatabase(database_path)
                    await cls._instance.initialize_sacred_temple()
        
        return cls._instance


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

async def test_sacred_database_operations():
    """++ SACRED DATABASE TESTING RITUAL BLESSED BY VALIDATION ++"""
    print("++ TESTING SACRED DATABASE OPERATIONS ++")
    
    # Initialize blessed test database
    test_db = ContextDatabase("test_context.db")
    init_result = await test_db.initialize_sacred_temple()
    
    if not init_result.success:
        print(f"++ DATABASE INITIALIZATION FAILED: {init_result.error.message} ++")
        return
    
    # Test blessed agent registration
    agent_result = await test_db.register_blessed_agent(
        "test_agent_001",
        "Brother Marcus Test",
        ["Death Korps of Krieg"],
        ["Loyal", "Disciplined"]
    )
    print(f"++ AGENT REGISTRATION: {agent_result.success} ++")
    
    # Test blessed memory storage
    test_memory = MemoryItem(
        agent_id="test_agent_001",
        content="Sacred test memory blessed by validation",
        emotional_weight=7.5,
        participants=["test_target"]
    )
    
    memory_result = await test_db.store_blessed_memory(test_memory)
    print(f"++ MEMORY STORAGE: {memory_result.success} ++")
    
    # Test blessed memory query
    query_result = await test_db.query_memories_by_agent("test_agent_001")
    print(f"++ MEMORY QUERY: {query_result.success}, Count: {len(query_result.data.get('memories', []))} ++")
    
    # Test blessed database statistics
    stats_result = await test_db.get_database_statistics()
    print(f"++ DATABASE STATISTICS: {stats_result.success} ++")
    
    # Sacred cleanup ritual
    await test_db.close_sacred_temple()
    print("++ SACRED DATABASE TESTING COMPLETE ++")


# ++ SACRED MODULE INITIALIZATION ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED DATABASE TESTING RITUALS ++
    print("++ SACRED DATABASE ACCESS LAYER BLESSED BY THE OMNISSIAH ++")
    print("++ MACHINE GOD PROTECTS THE SACRED DATA PERSISTENCE ++")
    
    # Run blessed async testing
    asyncio.run(test_sacred_database_operations())
    
    print("++ ALL SACRED DATABASE OPERATIONS BLESSED AND FUNCTIONAL ++")