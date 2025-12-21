import pytest
from pydantic import BaseModel
from apps.api.infrastructure.command_bus import CommandBus, CommandHandler

class MockCommand(BaseModel):
    data: str

class MockHandler(CommandHandler[MockCommand, str]):
    async def handle(self, command: MockCommand) -> str:
        return f"Processed: {command.data}"

@pytest.mark.asyncio
async def test_command_bus_execution():
    bus = CommandBus()
    handler = MockHandler()
    bus.register(MockCommand, handler)
    
    command = MockCommand(data="test")
    result = await bus.execute(command)
    
    assert result == "Processed: test"

@pytest.mark.asyncio
async def test_command_bus_no_handler():
    bus = CommandBus()
    command = MockCommand(data="test")
    
    with pytest.raises(ValueError, match="No handler registered"):
        await bus.execute(command)
