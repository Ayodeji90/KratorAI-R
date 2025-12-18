"""Tests for breeding functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from src.api.schemas import BreedRequest, ImageInput
from src.lineage.royalty_graph import RoyaltyGraph


class TestRoyaltyGraph:
    """Tests for RoyaltyGraph class."""
    
    def test_add_design(self):
        """Test adding a design to the graph."""
        graph = RoyaltyGraph()
        graph.add_design("design_1", "owner_1", is_original=True)
        
        assert "design_1" in graph.graph.nodes
        assert graph.graph.nodes["design_1"]["owner_id"] == "owner_1"
    
    def test_add_breeding_relationship(self):
        """Test adding a breeding relationship."""
        graph = RoyaltyGraph()
        graph.add_design("parent_1", "owner_1")
        graph.add_design("parent_2", "owner_2")
        graph.add_design("child_1", "owner_3", is_original=False)
        
        graph.add_breeding_relationship("parent_1", "child_1", 0.6)
        graph.add_breeding_relationship("parent_2", "child_1", 0.4)
        
        assert graph.graph.has_edge("parent_1", "child_1")
        assert graph.graph.edges["parent_1", "child_1"]["weight"] == 0.6
    
    def test_compute_shares(self):
        """Test computing royalty shares."""
        graph = RoyaltyGraph()
        graph.add_design("parent_1", "owner_1")
        graph.add_design("parent_2", "owner_2")
        
        inputs = [
            ImageInput(uri="gs://test/1.png", weight=0.6),
            ImageInput(uri="gs://test/2.png", weight=0.4),
        ]
        
        shares = graph.compute_shares(["parent_1", "parent_2"], inputs)
        
        assert len(shares) == 2
        assert shares[0].share_percentage == 60.0
        assert shares[1].share_percentage == 40.0
    
    def test_get_ancestors(self):
        """Test getting ancestors of a design."""
        graph = RoyaltyGraph()
        graph.add_design("grandparent", "owner_1")
        graph.add_design("parent", "owner_2")
        graph.add_design("child", "owner_3")
        
        graph.add_breeding_relationship("grandparent", "parent", 1.0)
        graph.add_breeding_relationship("parent", "child", 1.0)
        
        ancestors = graph.get_ancestors("child")
        
        assert "grandparent" in ancestors
        assert "parent" in ancestors
    
    def test_serialization(self):
        """Test graph serialization and deserialization."""
        graph = RoyaltyGraph()
        graph.add_design("design_1", "owner_1")
        graph.add_design("design_2", "owner_2")
        graph.add_breeding_relationship("design_1", "design_2", 0.5)
        
        data = graph.to_dict()
        restored = RoyaltyGraph.from_dict(data)
        
        assert "design_1" in restored.graph.nodes
        assert restored.graph.has_edge("design_1", "design_2")


class TestBreedRequest:
    """Tests for BreedRequest schema validation."""
    
    def test_valid_request(self):
        """Test valid breed request."""
        request = BreedRequest(
            images=[
                ImageInput(uri="gs://test/1.png", weight=0.5),
                ImageInput(uri="gs://test/2.png", weight=0.5),
            ],
            prompt="Blend with Lagos vibes",
        )
        
        assert len(request.images) == 2
        assert request.prompt == "Blend with Lagos vibes"
    
    def test_weight_validation(self):
        """Test that weights are validated."""
        with pytest.raises(ValueError):
            ImageInput(uri="gs://test/1.png", weight=1.5)  # > 1.0
    
    def test_min_images(self):
        """Test minimum images requirement."""
        with pytest.raises(ValueError):
            BreedRequest(
                images=[ImageInput(uri="gs://test/1.png", weight=1.0)],
            )  # Only 1 image
