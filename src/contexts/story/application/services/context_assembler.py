"""Context Assembler Service.

Compresses world state into an LLM-compatible prompt within token budget.
This is the "Memory" component of the AI writer, filtering and summarizing
relevant world information based on character proximity in the world graph.

DEV-001: Narrative Engine Context Builder
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Set

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

if TYPE_CHECKING:
    import networkx as nx


@dataclass(frozen=True)
class WorldNode:
    """Represents a node in the world graph.

    Nodes can be characters, locations, events, or factions.
    Each node has an ID, type, and associated data.
    """

    id: str
    node_type: str
    name: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextAssemblerInput:
    """Input for context assembly.

    Args:
        active_character_ids: IDs of characters currently active in the scene.
        max_tokens: Maximum token budget for output context.
        hop_distance: Maximum graph distance from characters to include.
        prioritize_recent: Whether to prioritize recently updated nodes.
    """

    active_character_ids: List[str]
    max_tokens: int = 4000
    hop_distance: int = 2
    prioritize_recent: bool = True


@dataclass
class ContextAssemblerResult:
    """Result of context assembly.

    Args:
        context_text: The assembled context as a text string.
        token_count: Actual token count of the assembled context.
        included_nodes: List of node IDs included in the context.
        truncated: Whether the context was truncated to fit token budget.
    """

    context_text: str
    token_count: int
    included_nodes: List[str]
    truncated: bool


class TokenCounterProtocol(Protocol):
    """Protocol for token counting implementations."""

    def count(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: The text to count tokens for.

        Returns:
            Number of tokens in the text.
        """
        ...


class TiktokenCounter:
    """Token counter using tiktoken library (GPT models).

    Uses cl100k_base encoding by default (GPT-4, GPT-3.5-turbo).
    """

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        """Initialize with specified encoding.

        Args:
            encoding_name: Name of the tiktoken encoding to use.
        """
        if not TIKTOKEN_AVAILABLE:
            raise ImportError(
                "tiktoken is not available. Install with: pip install tiktoken"
            )
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: The text to count tokens for.

        Returns:
            Number of tokens according to tiktoken encoding.
        """
        return len(self._encoding.encode(text))


class SimpleTokenCounter:
    """Simple token counter using word-based estimation.

    Fallback when tiktoken is not available. Uses rough estimate
    of ~4 characters per token (varies by content).
    """

    def count(self, text: str) -> int:
        """Estimate token count based on character/word count.

        Args:
            text: The text to count tokens for.

        Returns:
            Estimated number of tokens.
        """
        # Rough estimate: ~4 characters per token on average
        return max(1, len(text) // 4)


class ContextAssembler:
    """Assembles world context for narrative generation.

    Filters a world graph to include only nodes within N hops of active
    characters, then summarizes the resulting context to fit within a
    token budget.

    The assembly process:
    1. Identify active character nodes in the graph
    2. BFS to find all nodes within hop_distance
    3. Prioritize nodes by relevance (type, recency, connections)
    4. Format nodes into context text
    5. Truncate if necessary to fit token budget

    Example:
        >>> assembler = ContextAssembler()
        >>> result = assembler.assemble(
        ...     world_graph=graph,
        ...     input=ContextAssemblerInput(
        ...         active_character_ids=["char-001", "char-002"],
        ...         max_tokens=4000,
        ...         hop_distance=2,
        ...     )
        ... )
        >>> print(result.context_text)
    """

    def __init__(
        self,
        token_counter: Optional[TokenCounterProtocol] = None,
    ) -> None:
        """Initialize the context assembler.

        Args:
            token_counter: Token counter implementation. Defaults to tiktoken
                if available, otherwise uses simple estimation.
        """
        if token_counter is not None:
            self._counter = token_counter
        elif TIKTOKEN_AVAILABLE:
            self._counter = TiktokenCounter()
        else:
            self._counter = SimpleTokenCounter()

    def assemble(
        self,
        world_graph: "nx.Graph",
        input: ContextAssemblerInput,
    ) -> ContextAssemblerResult:
        """Assemble context from world graph within token budget.

        Args:
            world_graph: NetworkX graph representing the world state.
                Nodes should have 'type', 'name', and 'description' attributes.
            input: Configuration for context assembly.

        Returns:
            ContextAssemblerResult with assembled context and metadata.

        Raises:
            ValueError: If no active characters found in graph.
        """
        # Find nodes within hop distance of active characters
        relevant_nodes = self._find_relevant_nodes(
            world_graph,
            input.active_character_ids,
            input.hop_distance,
        )

        if not relevant_nodes:
            return ContextAssemblerResult(
                context_text="No relevant context found for active characters.",
                token_count=self._counter.count(
                    "No relevant context found for active characters."
                ),
                included_nodes=[],
                truncated=False,
            )

        # Convert graph nodes to WorldNode objects
        world_nodes = self._extract_world_nodes(world_graph, relevant_nodes)

        # Prioritize nodes
        prioritized = self._prioritize_nodes(
            world_nodes,
            input.active_character_ids,
            input.prioritize_recent,
        )

        # Assemble context text within token budget
        context_text, included_ids, truncated = self._assemble_with_budget(
            prioritized,
            input.max_tokens,
        )

        return ContextAssemblerResult(
            context_text=context_text,
            token_count=self._counter.count(context_text),
            included_nodes=included_ids,
            truncated=truncated,
        )

    def _find_relevant_nodes(
        self,
        graph: "nx.Graph",
        character_ids: List[str],
        hop_distance: int,
    ) -> Set[str]:
        """Find all nodes within hop_distance of active characters.

        Args:
            graph: The world graph.
            character_ids: IDs of active characters.
            hop_distance: Maximum distance to search.

        Returns:
            Set of node IDs within the specified distance.
        """
        try:
            import networkx as nx
        except ImportError:
            # Return character IDs as fallback if networkx unavailable
            return set(character_ids)

        relevant = set()

        for char_id in character_ids:
            if char_id not in graph:
                continue

            # BFS from character node
            try:
                lengths = nx.single_source_shortest_path_length(
                    graph, char_id, cutoff=hop_distance
                )
                relevant.update(lengths.keys())
            except nx.NetworkXError:
                # Node not in graph or disconnected
                relevant.add(char_id)

        return relevant

    def _extract_world_nodes(
        self,
        graph: "nx.Graph",
        node_ids: Set[str],
    ) -> List[WorldNode]:
        """Extract WorldNode objects from graph nodes.

        Args:
            graph: The world graph.
            node_ids: IDs of nodes to extract.

        Returns:
            List of WorldNode objects.
        """
        nodes = []
        for node_id in node_ids:
            if node_id not in graph:
                continue

            data = graph.nodes[node_id]
            nodes.append(
                WorldNode(
                    id=node_id,
                    node_type=data.get("type", "unknown"),
                    name=data.get("name", node_id),
                    description=data.get("description", ""),
                    metadata=dict(data),
                )
            )
        return nodes

    def _prioritize_nodes(
        self,
        nodes: List[WorldNode],
        character_ids: List[str],
        prioritize_recent: bool,
    ) -> List[WorldNode]:
        """Sort nodes by relevance priority.

        Priority order:
        1. Active characters
        2. Locations (setting context)
        3. Events (plot context)
        4. Other characters
        5. Other nodes

        Args:
            nodes: List of WorldNode objects.
            character_ids: IDs of active characters.
            prioritize_recent: Whether to boost recently updated nodes.

        Returns:
            Sorted list of WorldNode objects.
        """
        type_priority = {
            "character": 1,
            "location": 2,
            "event": 3,
            "faction": 4,
            "item": 5,
        }

        def sort_key(node: WorldNode) -> tuple:
            # Active characters come first
            is_active = node.id in character_ids
            type_order = type_priority.get(node.node_type, 10)

            # Recency (if available in metadata)
            recency = 0
            if prioritize_recent:
                updated_at = node.metadata.get("updated_at")
                if updated_at:
                    # Higher is more recent (timestamp as float)
                    try:
                        recency = -float(updated_at)
                    except (ValueError, TypeError):
                        pass

            return (not is_active, type_order, recency)

        return sorted(nodes, key=sort_key)

    def _assemble_with_budget(
        self,
        nodes: List[WorldNode],
        max_tokens: int,
    ) -> tuple[str, List[str], bool]:
        """Assemble context text respecting token budget.

        Args:
            nodes: Prioritized list of WorldNode objects.
            max_tokens: Maximum token budget.

        Returns:
            Tuple of (context_text, included_node_ids, was_truncated).
        """
        sections = []
        included_ids = []
        current_tokens = 0
        truncated = False

        # Header
        header = "# World Context\n\n"
        header_tokens = self._counter.count(header)
        if header_tokens >= max_tokens:
            return header.strip(), [], True

        current_tokens = header_tokens
        sections.append(header)

        # Group nodes by type for organized output
        grouped: Dict[str, List[WorldNode]] = {}
        for node in nodes:
            if node.node_type not in grouped:
                grouped[node.node_type] = []
            grouped[node.node_type].append(node)

        # Add sections by type
        for type_name, type_nodes in grouped.items():
            section_header = f"## {type_name.title()}s\n\n"
            section_tokens = self._counter.count(section_header)

            if current_tokens + section_tokens >= max_tokens:
                truncated = True
                break

            section_parts = [section_header]
            section_token_count = section_tokens

            for node in type_nodes:
                node_text = self._format_node(node)
                node_tokens = self._counter.count(node_text)

                if current_tokens + section_token_count + node_tokens >= max_tokens:
                    truncated = True
                    break

                section_parts.append(node_text)
                section_token_count += node_tokens
                included_ids.append(node.id)

            sections.extend(section_parts)
            current_tokens += section_token_count

            if truncated:
                break

        context_text = "".join(sections).strip()
        return context_text, included_ids, truncated

    def _format_node(self, node: WorldNode) -> str:
        """Format a single node as context text.

        Args:
            node: The WorldNode to format.

        Returns:
            Formatted text representation.
        """
        lines = [f"### {node.name}"]

        if node.description:
            lines.append(node.description)

        # Add relevant metadata
        metadata_keys = ["status", "alignment", "location", "faction"]
        for key in metadata_keys:
            if key in node.metadata:
                value = node.metadata[key]
                if value:
                    lines.append(f"- {key.title()}: {value}")

        lines.append("")  # Blank line between nodes
        return "\n".join(lines) + "\n"


def create_context_assembler(
    use_tiktoken: bool = True,
) -> ContextAssembler:
    """Factory function to create a ContextAssembler.

    Args:
        use_tiktoken: Whether to use tiktoken for accurate token counting.
            Falls back to simple estimation if False or tiktoken unavailable.

    Returns:
        Configured ContextAssembler instance.
    """
    counter: TokenCounterProtocol
    if use_tiktoken and TIKTOKEN_AVAILABLE:
        counter = TiktokenCounter()
    else:
        counter = SimpleTokenCounter()

    return ContextAssembler(token_counter=counter)
