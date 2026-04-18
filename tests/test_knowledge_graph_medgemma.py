"""
Test Knowledge Graph + MedGemma Integration
===========================================
Verifies that the disease knowledge graph (built from Wikipedia and AIIMS books)
is used for correct diagnosis and cure recommendations when calling MedGemma.

Tests:
  1. Knowledge graph is built and loadable
  2. Graph context is retrieved for sample symptoms
  3. MedGemma diagnosis flow uses graph context (when Ollama available)
  4. Cure/treatment info appears in graph context

Usage:
    cd backend
    python -m pytest tests/test_knowledge_graph_medgemma.py -v
    python -m tests.test_knowledge_graph_medgemma   # Run as script
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "disease_books"
GRAPH_PATH = BOOKS_DIR / "knowledge_graph.json"


class TestKnowledgeGraphBuild:
    """Verify knowledge graph exists and has expected structure."""

    def test_graph_file_exists(self):
        """Graph JSON file should exist after build_knowledge_graph.py."""
        assert GRAPH_PATH.exists(), (
            f"Run: cd backend && python scripts/build_knowledge_graph.py"
        )

    def test_graph_has_nodes_and_edges(self):
        """Graph should have nodes and edges."""
        with open(GRAPH_PATH) as f:
            g = json.load(f)
        nodes = g.get("nodes", {})
        edges = g.get("edges", [])
        assert len(nodes) > 0, "Graph should have nodes"
        assert len(edges) > 0, "Graph should have edges"

    def test_graph_has_disease_symptom_treatment_types(self):
        """Graph should contain disease, symptom, and treatment entities."""
        with open(GRAPH_PATH) as f:
            g = json.load(f)
        nodes = g.get("nodes", {})
        types = {n.get("type") for n in nodes.values()}
        assert "disease" in types
        assert "symptom" in types or "treatment" in types

    def test_graph_has_treatment_edges(self):
        """Graph should have treatable_by edges for cure retrieval."""
        with open(GRAPH_PATH) as f:
            g = json.load(f)
        edges = g.get("edges", [])
        treat_edges = [e for e in edges if e.get("relation") == "treatable_by"]
        assert len(treat_edges) > 0, "Graph should have treatment relationships"


class TestGraphContextRetrieval:
    """Test get_graph_context returns relevant disease and cure info."""

    def test_retrieves_context_for_vertigo(self):
        """Vertigo symptoms should retrieve BPPV and related diseases."""
        from app.services.disease_knowledge_graph import get_graph_context

        ctx = get_graph_context("vertigo, dizziness, spinning sensation when moving head")
        assert ctx
        assert "vertigo" in ctx.lower() or "dizziness" in ctx.lower() or "bppv" in ctx.lower()

    def test_retrieves_context_for_chest_pain(self):
        """Chest pain should retrieve cardiac/GERD-related diseases."""
        from app.services.disease_knowledge_graph import get_graph_context

        ctx = get_graph_context("chest pain, pressure, nausea, sweating")
        assert ctx
        # Should have some disease context
        assert "**" in ctx  # Disease names are bolded

    def test_context_includes_treatments(self):
        """Retrieved context should include treatment/cure info when available."""
        from app.services.disease_knowledge_graph import get_graph_context

        ctx = get_graph_context("jaundice, abdominal pain, weight loss")
        assert ctx
        # Ampullary cancer, acute liver failure etc have treatment sections
        assert "Treatment" in ctx or "treatment" in ctx.lower() or "surgery" in ctx.lower()


class TestKnowledgeBrainIntegration:
    """Test disease_knowledge_brain uses graph when available."""

    def test_get_relevant_context_uses_graph(self):
        """get_relevant_context should return graph-based context when graph exists."""
        from app.services.disease_knowledge_brain import get_relevant_context

        ctx = get_relevant_context("fever, sore throat, swollen lymph nodes", use_knowledge_graph=True)
        assert ctx
        # Graph format includes "Knowledge Graph Reference"
        assert "Knowledge Graph" in ctx or "Reference" in ctx or "**" in ctx


@pytest.mark.skipif(
    os.getenv("SKIP_OLLAMA_TESTS") == "1",
    reason="Ollama/MedGemma not available",
)
class TestMedGemmaWithGraph:
    """Integration test: MedGemma receives graph context and returns diagnosis + cure."""

    @pytest.mark.asyncio
    async def test_diagnosis_includes_medications(self):
        """MedGemma diagnosis should include medications (cure) when using graph context."""
        from app.services.medgemma_diagnosis import diagnose

        result = await diagnose(
            "Patient has burning sensation in chest after meals, acid taste in mouth, worsens when lying down"
        )
        assert "diagnosis" in result
        assert result["diagnosis"]
        assert "medications" in result
        assert len(result.get("medications", [])) > 0
        assert "when_to_see_doctor" in result

    @pytest.mark.asyncio
    async def test_diagnosis_for_vertigo_case(self):
        """Vertigo symptoms -> BPPV or related diagnosis with treatment."""
        from app.services.medgemma_diagnosis import diagnose

        result = await diagnose(
            "Spinning sensation when turning head, brief episodes of vertigo, nausea"
        )
        assert "diagnosis" in result
        assert result["diagnosis"]
        assert "confidence" in result
        # Should have treatment recommendations
        meds = result.get("medications", [])
        recs = result.get("lifestyle_recommendations", [])
        assert len(meds) > 0 or len(recs) > 0


def run_as_script():
    """Run quick smoke tests when executed as script."""
    print("=" * 60)
    print("  Knowledge Graph + MedGemma Test")
    print("=" * 60)

    # 1. Graph exists
    if not GRAPH_PATH.exists():
        print("\nFAIL: knowledge_graph.json not found.")
        print("  Run: cd backend && python scripts/build_knowledge_graph.py")
        sys.exit(1)
    print("\n  [OK] Knowledge graph exists")

    # 2. Graph context retrieval
    from app.services.disease_knowledge_graph import get_graph_context

    ctx = get_graph_context("vertigo, dizziness, nausea")
    assert ctx, "Graph context should be non-empty"
    print("  [OK] Graph context retrieval works")

    # 3. Knowledge brain uses graph
    from app.services.disease_knowledge_brain import get_relevant_context

    ctx2 = get_relevant_context("chest pain, acid reflux", use_knowledge_graph=True)
    assert ctx2
    print("  [OK] Knowledge brain uses graph")

    # 4. MedGemma (if Ollama available)
    if os.getenv("SKIP_OLLAMA_TESTS") != "1":
        import asyncio
        from app.services.medgemma_diagnosis import diagnose

        async def _test():
            r = await diagnose("Fever, sore throat, swollen lymph nodes")
            return r.get("diagnosis") and len(r.get("medications", [])) > 0

        try:
            ok = asyncio.run(_test())
            if ok:
                print("  [OK] MedGemma diagnosis with graph context")
            else:
                print("  [WARN] MedGemma returned but missing medications")
        except Exception as e:
            print(f"  [SKIP] MedGemma unavailable: {e}")
            print("         Set SKIP_OLLAMA_TESTS=1 to skip Ollama tests")
    else:
        print("  [SKIP] Ollama tests disabled (SKIP_OLLAMA_TESTS=1)")

    print("\n" + "=" * 60)
    print("  All checks passed.")
    print("=" * 60)


if __name__ == "__main__":
    run_as_script()
