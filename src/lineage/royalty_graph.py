"""Royalty graph for tracking design lineage and computing shares."""

import networkx as nx
from typing import Optional
from dataclasses import dataclass

from src.api.schemas import RoyaltyShare, ImageInput


@dataclass
class DesignNode:
    """Represents a design in the lineage graph."""
    design_id: str
    owner_id: str
    created_at: str
    is_original: bool = True


class RoyaltyGraph:
    """
    NetworkX-based graph for tracking design lineage and computing royalties.
    
    Each node is a design, each edge represents a parent-child relationship
    with an associated weight (share of contribution).
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def add_design(self, design_id: str, owner_id: str, is_original: bool = True) -> None:
        """Add a design node to the graph."""
        self.graph.add_node(
            design_id,
            owner_id=owner_id,
            is_original=is_original,
        )
    
    def add_breeding_relationship(
        self,
        parent_id: str,
        child_id: str,
        weight: float,
    ) -> None:
        """
        Add a parent-child breeding relationship.
        
        Args:
            parent_id: ID of the parent design
            child_id: ID of the bred (child) design
            weight: Contribution weight of this parent (0-1)
        """
        self.graph.add_edge(parent_id, child_id, weight=weight)
    
    def compute_shares(
        self,
        parent_ids: list[str],
        inputs: list[ImageInput],
    ) -> list[RoyaltyShare]:
        """
        Compute royalty shares for a bred design.
        
        For simple breeding, shares are proportional to input weights.
        For multi-generation breeding, shares propagate up the lineage tree.
        
        Args:
            parent_ids: List of parent design IDs
            inputs: Original input images with weights
        
        Returns:
            List of RoyaltyShare objects
        """
        shares = []
        
        for parent_id, input_img in zip(parent_ids, inputs):
            # Get owner from graph, or use placeholder
            owner_id = self.graph.nodes.get(parent_id, {}).get("owner_id", f"owner_{parent_id}")
            
            # For multi-generation, we'd recursively compute shares
            # For now, use direct weights
            share = RoyaltyShare(
                design_id=parent_id,
                owner_id=owner_id,
                share_percentage=input_img.weight * 100,
            )
            shares.append(share)
        
        return shares
    
    def compute_propagated_shares(self, design_id: str) -> dict[str, float]:
        """
        Compute propagated shares for all ancestors of a design.
        
        This traces back through the entire lineage to compute
        what percentage each original creator should receive.
        
        Args:
            design_id: ID of the design to trace
        
        Returns:
            Dict of owner_id -> total share percentage
        """
        owner_shares: dict[str, float] = {}
        
        def trace_ancestry(node_id: str, share_multiplier: float = 1.0):
            """Recursively trace ancestry and accumulate shares."""
            predecessors = list(self.graph.predecessors(node_id))
            
            if not predecessors:
                # This is an original design
                owner_id = self.graph.nodes[node_id].get("owner_id")
                if owner_id:
                    owner_shares[owner_id] = owner_shares.get(owner_id, 0) + share_multiplier
                return
            
            for pred in predecessors:
                edge_weight = self.graph.edges[pred, node_id].get("weight", 0.5)
                trace_ancestry(pred, share_multiplier * edge_weight)
        
        trace_ancestry(design_id)
        
        # Normalize to percentages
        total = sum(owner_shares.values())
        if total > 0:
            owner_shares = {k: (v / total) * 100 for k, v in owner_shares.items()}
        
        return owner_shares
    
    def get_ancestors(self, design_id: str) -> list[str]:
        """Get all ancestors of a design."""
        return list(nx.ancestors(self.graph, design_id))
    
    def get_descendants(self, design_id: str) -> list[str]:
        """Get all descendants of a design."""
        return list(nx.descendants(self.graph, design_id))
    
    def to_dict(self) -> dict:
        """Serialize graph to dictionary."""
        return nx.node_link_data(self.graph)
    
    @classmethod
    def from_dict(cls, data: dict) -> "RoyaltyGraph":
        """Deserialize graph from dictionary."""
        instance = cls()
        instance.graph = nx.node_link_graph(data)
        return instance
