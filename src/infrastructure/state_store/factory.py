def create_unified_state_manager(
    config: Optional[StateStoreConfig] = None,
) -> UnifiedStateManager:
    """Create unified state manager"""
    if config is None:
        config_manager = ConfigurationManager()
        config_manager.load_configuration()
        config = config_manager.get_state_store_config()

    return UnifiedStateManager(config)


def create_configuration_manager(
    config_paths: Optional[List[str]] = None,
) -> ConfigurationManager:
    """Create configuration manager"""
    return ConfigurationManager(config_paths)


if __name__ == "__main__":
    # Example usage
    async def example_usage():
        # Load configuration
        config_manager = create_configuration_manager()
        config_manager.load_configuration()

        # Create state manager
        state_manager = create_unified_state_manager()
        await state_manager.initialize()

        # Test different data types
        # Session data (Redis)
        session_key = StateKey("game_session", "session", "player_123")
        await state_manager.set(
            session_key, {"player_id": "123", "current_location": "forest"}
        )

        # Agent state (PostgreSQL)
        agent_key = StateKey("simulation", "agent", "alice")
        await state_manager.set(
            agent_key, {"name": "Alice", "personality": {"curiosity": 0.8}}
        )

        # Narrative document (S3)
        narrative_key = StateKey("story", "narrative", "chapter_1")
        await state_manager.set(
            narrative_key, "In the beginning, there was a mysterious forest..."
        )

        # Retrieve data
        session_data = await state_manager.get(session_key)
        agent_data = await state_manager.get(agent_key)
        narrative_data = await state_manager.get(narrative_key)

        logger.info(f"Session: {session_data}")
        logger.info(f"Agent: {agent_data}")
        logger.info(f"Narrative: {narrative_data}")

        # Health check
        health = await state_manager.health_check()
        logger.info(f"Health: {health}")

        # Cleanup
        await state_manager.close()

    # Run example
    # asyncio.run(example_usage())
