#!/usr/bin/env python3
"""
Causal Graph Domain Service

This module implements the CausalGraphService, a key domain service for
managing cause-and-effect relationships within narrative structures.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from ..value_objects.causal_node import CausalNode, CausalRelationType, CausalStrength

logger = logging.getLogger(__name__)


@dataclass
class CausalPath:
    """Represents a path through the causal graph."""

    nodes: List[str]
    total_strength: Decimal
    path_length: int
    relationship_types: List[CausalRelationType]

    @property
    def average_strength(self) -> Decimal:
        """Calculate average relationship strength along path."""
        if self.path_length == 0:
            return Decimal("0")
        return self.total_strength / Decimal(str(self.path_length))


@dataclass
class CausalAnalysis:
    """Results of causal analysis."""

    root_causes: List[str]
    terminal_effects: List[str]
    critical_nodes: List[str]
    feedback_loops: List[List[str]]
    longest_chains: List[CausalPath]
    graph_complexity: Decimal
    consistency_score: Decimal
    narrative_flow_score: Decimal


class CausalGraphService:
    """
    Domain service for managing causal relationships in narratives.

    Provides sophisticated analysis of cause-and-effect relationships,
    consistency checking, and narrative flow optimization.
    """

    def __init__(self):
        """Initialize the causal graph service."""
        self.nodes: Dict[str, CausalNode] = {}
        self._relationship_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._analysis_cache: Optional[CausalAnalysis] = None
        self._cache_valid = False

    def add_node(self, node: CausalNode) -> None:
        """
        Add a causal node to the graph.

        Args:
            node: CausalNode to add to the graph
        """
        self.nodes[node.node_id] = node
        self._invalidate_cache()
        logger.debug(f"Added causal node: {node.node_id}")

    def remove_node(self, node_id: str) -> Optional[CausalNode]:
        """
        Remove a causal node from the graph.

        Args:
            node_id: ID of node to remove

        Returns:
            Removed node, or None if not found
        """
        if node_id not in self.nodes:
            return None

        removed_node = self.nodes.pop(node_id)

        # Remove references to this node from other nodes
        for node in self.nodes.values():
            node.direct_causes.discard(node_id)
            node.direct_effects.discard(node_id)
            node.indirect_causes.discard(node_id)
            node.indirect_effects.discard(node_id)
            if node_id in node.causal_relationships:
                del node.causal_relationships[node_id]

        self._invalidate_cache()
        logger.debug(f"Removed causal node: {node_id}")
        return removed_node

    def establish_causal_link(
        self,
        cause_id: str,
        effect_id: str,
        relationship_type: CausalRelationType = CausalRelationType.DIRECT_CAUSE,
        strength: CausalStrength = CausalStrength.MODERATE,
        certainty: Decimal = Decimal("0.8"),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Establish a causal relationship between two nodes.

        Args:
            cause_id: ID of the causing node
            effect_id: ID of the effect node
            relationship_type: Type of causal relationship
            strength: Strength of the relationship
            certainty: Certainty level (0-1)
            metadata: Additional relationship metadata

        Returns:
            True if relationship was established successfully
        """
        if cause_id not in self.nodes or effect_id not in self.nodes:
            logger.warning(f"Cannot establish link: nodes {cause_id} or {effect_id} not found")
            return False

        if cause_id == effect_id:
            logger.warning(f"Cannot establish self-referential causal link: {cause_id}")
            return False

        # Check for circular dependencies
        if self._would_create_cycle(cause_id, effect_id):
            logger.warning(f"Causal link {cause_id} -> {effect_id} would create cycle")
            return False

        cause_node = self.nodes[cause_id]
        effect_node = self.nodes[effect_id]

        # Add relationship to cause node
        if relationship_type == CausalRelationType.DIRECT_CAUSE:
            cause_node.direct_effects.add(effect_id)
        else:
            cause_node.indirect_effects.add(effect_id)

        cause_node.causal_relationships[effect_id] = {
            "relationship_type": relationship_type.value,
            "strength": strength.value,
            "certainty": float(certainty),
            "direction": "outgoing",
            "metadata": metadata or {},
        }

        # Add relationship to effect node
        if relationship_type == CausalRelationType.DIRECT_CAUSE:
            effect_node.direct_causes.add(cause_id)
        else:
            effect_node.indirect_causes.add(cause_id)

        effect_node.causal_relationships[cause_id] = {
            "relationship_type": relationship_type.value,
            "strength": strength.value,
            "certainty": float(certainty),
            "direction": "incoming",
            "metadata": metadata or {},
        }

        self._invalidate_cache()
        logger.info(
            f"Established causal link: {cause_id} --{relationship_type.value}--> {effect_id}"
        )
        return True

    def remove_causal_link(self, cause_id: str, effect_id: str) -> bool:
        """
        Remove a causal relationship between two nodes.

        Args:
            cause_id: ID of the causing node
            effect_id: ID of the effect node

        Returns:
            True if relationship was removed successfully
        """
        if cause_id not in self.nodes or effect_id not in self.nodes:
            return False

        cause_node = self.nodes[cause_id]
        effect_node = self.nodes[effect_id]

        # Remove from cause node
        cause_node.direct_effects.discard(effect_id)
        cause_node.indirect_effects.discard(effect_id)
        cause_node.causal_relationships.pop(effect_id, None)

        # Remove from effect node
        effect_node.direct_causes.discard(cause_id)
        effect_node.indirect_causes.discard(cause_id)
        effect_node.causal_relationships.pop(cause_id, None)

        self._invalidate_cache()
        logger.info(f"Removed causal link: {cause_id} -> {effect_id}")
        return True

    def _would_create_cycle(self, cause_id: str, effect_id: str) -> bool:
        """Check if adding a link would create a cycle."""
        # Use DFS to see if effect_id can reach cause_id
        visited = set()
        stack = [effect_id]

        while stack:
            current = stack.pop()
            if current == cause_id:
                return True

            if current in visited:
                continue

            visited.add(current)

            if current in self.nodes:
                node = self.nodes[current]
                stack.extend(node.direct_effects)
                stack.extend(node.indirect_effects)

        return False

    def find_causal_paths(
        self, start_node: str, end_node: str, max_depth: int = 5
    ) -> List[CausalPath]:
        """
        Find all causal paths between two nodes.

        Args:
            start_node: Starting node ID
            end_node: Ending node ID
            max_depth: Maximum path depth to search

        Returns:
            List of CausalPath objects representing paths
        """
        if start_node not in self.nodes or end_node not in self.nodes:
            return []

        paths = []
        self._find_paths_recursive(
            start_node, end_node, [start_node], [], Decimal("1.0"), max_depth, paths
        )

        # Sort by strength and path length
        paths.sort(key=lambda p: (-float(p.average_strength), p.path_length))
        return paths

    def _find_paths_recursive(
        self,
        current: str,
        target: str,
        path: List[str],
        rel_types: List[CausalRelationType],
        cumulative_strength: Decimal,
        remaining_depth: int,
        paths: List[CausalPath],
    ) -> None:
        """Recursively find paths between nodes."""
        if remaining_depth <= 0:
            return

        if current not in self.nodes:
            return

        node = self.nodes[current]

        # Check all outgoing relationships
        for next_node in node.direct_effects.union(node.indirect_effects):
            if next_node in path:  # Avoid cycles
                continue

            rel_info = node.causal_relationships.get(next_node, {})
            rel_type_str = rel_info.get("relationship_type", "direct_cause")
            rel_type = CausalRelationType(rel_type_str)

            strength_str = rel_info.get("strength", "moderate")
            strength_modifier = self._get_strength_modifier(CausalStrength(strength_str))

            new_strength = cumulative_strength * strength_modifier
            new_path = path + [next_node]
            new_rel_types = rel_types + [rel_type]

            if next_node == target:
                # Found a path to target
                causal_path = CausalPath(
                    nodes=new_path,
                    total_strength=new_strength,
                    path_length=len(new_path) - 1,
                    relationship_types=new_rel_types,
                )
                paths.append(causal_path)
            else:
                # Continue searching
                self._find_paths_recursive(
                    next_node,
                    target,
                    new_path,
                    new_rel_types,
                    new_strength,
                    remaining_depth - 1,
                    paths,
                )

    def _get_strength_modifier(self, strength: CausalStrength) -> Decimal:
        """Convert strength enum to decimal modifier."""
        strength_map = {
            CausalStrength.ABSOLUTE: Decimal("1.0"),
            CausalStrength.VERY_STRONG: Decimal("0.95"),
            CausalStrength.STRONG: Decimal("0.8"),
            CausalStrength.MODERATE: Decimal("0.6"),
            CausalStrength.WEAK: Decimal("0.4"),
            CausalStrength.VERY_WEAK: Decimal("0.2"),
            CausalStrength.NEGLIGIBLE: Decimal("0.05"),
        }
        return strength_map.get(strength, Decimal("0.6"))

    def analyze_narrative_causality(self) -> CausalAnalysis:
        """
        Perform comprehensive analysis of the causal graph.

        Returns:
            CausalAnalysis with detailed insights
        """
        if self._cache_valid and self._analysis_cache:
            return self._analysis_cache

        # Find root causes (nodes with no incoming causes)
        root_causes = [
            node_id
            for node_id, node in self.nodes.items()
            if not node.has_causes and node.has_effects
        ]

        # Find terminal effects (nodes with no outgoing effects)
        terminal_effects = [
            node_id
            for node_id, node in self.nodes.items()
            if node.has_causes and not node.has_effects
        ]

        # Find critical nodes (high impact or complexity)
        critical_nodes = self._identify_critical_nodes()

        # Detect feedback loops
        feedback_loops = self._detect_feedback_loops()

        # Find longest causal chains
        longest_chains = self._find_longest_chains()

        # Calculate graph metrics
        graph_complexity = self._calculate_graph_complexity()
        consistency_score = self._calculate_consistency_score()
        narrative_flow_score = self._calculate_narrative_flow_score()

        analysis = CausalAnalysis(
            root_causes=root_causes,
            terminal_effects=terminal_effects,
            critical_nodes=critical_nodes,
            feedback_loops=feedback_loops,
            longest_chains=longest_chains,
            graph_complexity=graph_complexity,
            consistency_score=consistency_score,
            narrative_flow_score=narrative_flow_score,
        )

        self._analysis_cache = analysis
        self._cache_valid = True

        return analysis

    def _identify_critical_nodes(self) -> List[str]:
        """Identify nodes that are critical to narrative flow."""
        critical = []

        for node_id, node in self.nodes.items():
            # Node is critical if:
            # 1. High narrative importance
            # 2. High connectivity (many causes/effects)
            # 3. Branch point or convergence point
            importance_score = node.overall_impact_score
            connectivity_score = Decimal(str(node.total_causes + node.total_effects))

            criticality_score = importance_score + (connectivity_score * Decimal("0.5"))

            if node.is_branch_point:
                criticality_score += Decimal("2.0")
            if node.is_convergence_point:
                criticality_score += Decimal("2.0")

            if criticality_score >= Decimal("8.0"):
                critical.append(node_id)

        return critical

    def _detect_feedback_loops(self) -> List[List[str]]:
        """Detect feedback loops in the causal graph."""
        feedback_loops = []
        visited = set()
        rec_stack = set()

        def dfs_cycle_detection(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            current_path = path + [node_id]

            if node_id in self.nodes:
                node = self.nodes[node_id]
                for neighbor in node.direct_effects.union(node.indirect_effects):
                    if neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = current_path.index(neighbor)
                        cycle = current_path[cycle_start:] + [neighbor]
                        if len(cycle) > 2:  # Meaningful cycle
                            feedback_loops.append(cycle)
                    elif neighbor not in visited:
                        dfs_cycle_detection(neighbor, current_path)

            rec_stack.remove(node_id)

        for node_id in self.nodes:
            if node_id not in visited:
                dfs_cycle_detection(node_id, [])

        return feedback_loops

    def _find_longest_chains(self, max_chains: int = 5) -> List[CausalPath]:
        """Find the longest causal chains in the graph."""
        all_chains = []

        # Start from root causes
        root_causes = [node_id for node_id, node in self.nodes.items() if not node.has_causes]

        for root in root_causes:
            chains = self._get_chains_from_node(root)
            all_chains.extend(chains)

        # Sort by path length and strength
        all_chains.sort(key=lambda c: (-c.path_length, -float(c.average_strength)))

        return all_chains[:max_chains]

    def _get_chains_from_node(
        self, start_node: str, visited: Optional[Set[str]] = None
    ) -> List[CausalPath]:
        """Get all chains starting from a specific node."""
        if visited is None:
            visited = set()

        if start_node in visited or start_node not in self.nodes:
            return []

        visited = visited.copy()
        visited.add(start_node)

        node = self.nodes[start_node]
        chains = []

        if not node.has_effects:
            # Terminal node - create single-node chain
            chains.append(
                CausalPath(
                    nodes=[start_node],
                    total_strength=Decimal("1.0"),
                    path_length=0,
                    relationship_types=[],
                )
            )
        else:
            # Continue chains through effects
            for effect_id in node.direct_effects.union(node.indirect_effects):
                if effect_id not in visited:
                    sub_chains = self._get_chains_from_node(effect_id, visited)

                    rel_info = node.causal_relationships.get(effect_id, {})
                    rel_type_str = rel_info.get("relationship_type", "direct_cause")
                    rel_type = CausalRelationType(rel_type_str)
                    strength_str = rel_info.get("strength", "moderate")
                    strength_modifier = self._get_strength_modifier(CausalStrength(strength_str))

                    for sub_chain in sub_chains:
                        extended_chain = CausalPath(
                            nodes=[start_node] + sub_chain.nodes,
                            total_strength=strength_modifier * sub_chain.total_strength,
                            path_length=sub_chain.path_length + 1,
                            relationship_types=[rel_type] + sub_chain.relationship_types,
                        )
                        chains.append(extended_chain)

        return chains

    def _calculate_graph_complexity(self) -> Decimal:
        """Calculate overall graph complexity score."""
        if not self.nodes:
            return Decimal("0")

        # Base complexity from node count
        node_count = len(self.nodes)
        base_complexity = Decimal(str(node_count * 0.1))

        # Add complexity from relationships
        total_relationships = (
            sum(
                len(node.direct_causes)
                + len(node.direct_effects)
                + len(node.indirect_causes)
                + len(node.indirect_effects)
                for node in self.nodes.values()
            )
            / 2
        )  # Divide by 2 since each relationship is counted twice

        relationship_complexity = Decimal(str(total_relationships * 0.2))

        # Add complexity from special node types
        special_nodes = sum(
            1 for node in self.nodes.values() if node.is_branch_point or node.is_convergence_point
        )
        special_complexity = Decimal(str(special_nodes * 0.5))

        total_complexity = base_complexity + relationship_complexity + special_complexity
        return min(total_complexity, Decimal("10.0"))

    def _calculate_consistency_score(self) -> Decimal:
        """Calculate causal consistency score."""
        if not self.nodes:
            return Decimal("10.0")

        consistency_score = Decimal("10.0")

        # Check for orphaned nodes (no relationships)
        orphaned_count = sum(1 for node in self.nodes.values() if node.is_isolated)
        consistency_score -= Decimal(str(orphaned_count * 0.5))

        # Check for extremely weak causal chains
        weak_chains = 0
        for node in self.nodes.values():
            for rel_id, rel_info in node.causal_relationships.items():
                strength_str = rel_info.get("strength", "moderate")
                if strength_str in ["very_weak", "negligible"]:
                    weak_chains += 1

        consistency_score -= Decimal(str(weak_chains * 0.2))

        # Check for temporal inconsistencies
        temporal_issues = self._check_temporal_consistency()
        consistency_score -= Decimal(str(temporal_issues * 0.3))

        return max(Decimal("1.0"), consistency_score)

    def _check_temporal_consistency(self) -> int:
        """Check for temporal inconsistencies in causal relationships."""
        issues = 0

        for node in self.nodes.values():
            if node.sequence_order is None:
                continue

            # Check that causes come before effects temporally
            for cause_id in node.direct_causes.union(node.indirect_causes):
                if cause_id in self.nodes:
                    cause_node = self.nodes[cause_id]
                    if (
                        cause_node.sequence_order is not None
                        and cause_node.sequence_order >= node.sequence_order
                    ):
                        issues += 1

        return issues

    def _calculate_narrative_flow_score(self) -> Decimal:
        """Calculate how well the causal graph supports narrative flow."""
        if not self.nodes:
            return Decimal("5.0")

        flow_score = Decimal("5.0")

        # Reward clear progression from root causes to terminal effects
        root_causes = [n for n in self.nodes.values() if not n.has_causes and n.has_effects]
        terminal_effects = [n for n in self.nodes.values() if n.has_causes and not n.has_effects]

        if root_causes and terminal_effects:
            flow_score += Decimal("2.0")

        # Reward appropriate pacing (not too sparse, not too dense)
        avg_connectivity = sum(n.total_causes + n.total_effects for n in self.nodes.values()) / len(
            self.nodes
        )
        if 2.0 <= avg_connectivity <= 4.0:  # Sweet spot for narrative pacing
            flow_score += Decimal("1.5")

        # Penalize excessive complexity
        if len(self.nodes) > 50:  # Very complex graph
            flow_score -= Decimal("1.0")

        # Reward balanced branching and convergence
        branch_points = sum(1 for n in self.nodes.values() if n.is_branch_point)
        convergence_points = sum(1 for n in self.nodes.values() if n.is_convergence_point)

        if abs(branch_points - convergence_points) <= 2:  # Balanced
            flow_score += Decimal("1.0")

        return min(Decimal("10.0"), max(Decimal("1.0"), flow_score))

    def get_node_influence_score(self, node_id: str) -> Decimal:
        """
        Calculate the influence score of a specific node.

        Based on its position in the causal graph and relationships.
        """
        if node_id not in self.nodes:
            return Decimal("0")

        node = self.nodes[node_id]

        # Base influence from direct impact
        base_influence = node.overall_impact_score

        # Add influence from connectivity
        connectivity_bonus = Decimal(str((node.total_causes + node.total_effects) * 0.2))

        # Add influence from being a critical junction
        junction_bonus = Decimal("0")
        if node.is_branch_point:
            junction_bonus += Decimal("1.5")
        if node.is_convergence_point:
            junction_bonus += Decimal("1.0")

        # Add influence from downstream effects
        downstream_influence = self._calculate_downstream_influence(node_id, visited=set())

        total_influence = (
            base_influence + connectivity_bonus + junction_bonus + downstream_influence
        )
        return min(Decimal("10.0"), total_influence)

    def _calculate_downstream_influence(
        self, node_id: str, visited: Set[str], depth: int = 0
    ) -> Decimal:
        """Calculate influence this node has on downstream nodes."""
        if depth > 3 or node_id in visited or node_id not in self.nodes:  # Limit recursion depth
            return Decimal("0")

        visited = visited.copy()
        visited.add(node_id)

        node = self.nodes[node_id]
        downstream_influence = Decimal("0")

        for effect_id in node.direct_effects:
            if effect_id in self.nodes and effect_id not in visited:
                effect_node = self.nodes[effect_id]
                rel_info = node.causal_relationships.get(effect_id, {})
                strength_str = rel_info.get("strength", "moderate")
                strength_modifier = self._get_strength_modifier(CausalStrength(strength_str))

                # Add weighted influence from this effect
                effect_influence = effect_node.overall_impact_score * strength_modifier
                downstream_influence += effect_influence * Decimal("0.5")  # Decay factor

                # Add recursive downstream influence (with decay)
                recursive_influence = self._calculate_downstream_influence(
                    effect_id, visited, depth + 1
                )
                downstream_influence += recursive_influence * Decimal("0.3")

        return downstream_influence

    def _invalidate_cache(self) -> None:
        """Invalidate cached analysis results."""
        self._cache_valid = False
        self._relationship_cache.clear()
        self._analysis_cache = None

    def get_graph_summary(self) -> Dict[str, Any]:
        """Get a summary of the current causal graph state."""
        analysis = self.analyze_narrative_causality()

        return {
            "total_nodes": len(self.nodes),
            "root_causes_count": len(analysis.root_causes),
            "terminal_effects_count": len(analysis.terminal_effects),
            "critical_nodes_count": len(analysis.critical_nodes),
            "feedback_loops_count": len(analysis.feedback_loops),
            "longest_chain_length": max(
                (c.path_length for c in analysis.longest_chains), default=0
            ),
            "graph_complexity": float(analysis.graph_complexity),
            "consistency_score": float(analysis.consistency_score),
            "narrative_flow_score": float(analysis.narrative_flow_score),
            "total_relationships": sum(
                len(node.direct_causes) + len(node.direct_effects) for node in self.nodes.values()
            )
            // 2,
            "average_connectivity": (
                sum(node.total_causes + node.total_effects for node in self.nodes.values())
                / len(self.nodes)
                if self.nodes
                else 0
            ),
        }
