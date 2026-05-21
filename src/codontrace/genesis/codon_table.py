"""GENESIS codon table helpers."""

from __future__ import annotations

from codontrace.codon import CodonTable


class GenesisCodonTable:
    """Factory namespace for stable GENESIS codon table versions."""

    @staticmethod
    def default_v0() -> CodonTable:
        """Return the eight-codon GENESIS v0 table."""

        return CodonTable.genesis_v0()
