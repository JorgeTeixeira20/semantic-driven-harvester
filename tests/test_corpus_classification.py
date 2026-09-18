from __future__ import annotations

import csv
import unittest
from pathlib import Path

from semantic_harvester.corpus_classification import (
    REASON_ARTIGO, REASON_CAPTURES_OUTLIER, REASON_OBJECT_MOVED,
    REASON_SABERMAIS, classify, classify_corpus,
)
from tests.support import OfflineTestCase

PHASE1_FIELDS = (
    "original_url", "tstamp", "title", "facets", "queries",
    "num_queries_matched", "divergent",
)
PHASE2_FIELDS = (
    "original_url", "captures", "estimated_total", "requests_made", "error",
)


def write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


class ClassifyUnitTests(unittest.TestCase):
    """Testa classify() diretamente, sem passar pelos CSV agregados."""

    def test_low_capture_detalhe_page_is_artigo(self) -> None:
        result = classify(
            "https://www.record.pt/futebol/detalhe/exemplo-noticia-sintetica",
            "Exemplo de notícia sintética - Futebol - Jornal Record",
            captures=3,
        )
        self.assertTrue(result.is_artigo)
        self.assertEqual(result.reason, REASON_ARTIGO)

    def test_amp_article_without_detalhe_is_still_artigo(self) -> None:
        result = classify(
            "https://www.record.pt/futebol/amp/exemplo-noticia-amp",
            "Exemplo de notícia AMP - Futebol - Jornal Record",
            captures=2,
        )
        self.assertTrue(result.is_artigo)
        self.assertEqual(result.reason, REASON_ARTIGO)

    def test_sabermais_profile_page_is_excluded(self) -> None:
        result = classify(
            "https://www.record.pt/sabermais/exemplo-jogador",
            "Saber Mais: Exemplo Jogador",
            captures=250,
        )
        self.assertFalse(result.is_artigo)
        self.assertEqual(result.reason, REASON_SABERMAIS)

    def test_object_moved_title_is_excluded(self) -> None:
        result = classify(
            "http://www.record.pt/Futebol/Nacional/interior.aspx?content_id/x3d123456",
            "Object moved",
            captures=3,
        )
        self.assertFalse(result.is_artigo)
        self.assertEqual(result.reason, REASON_OBJECT_MOVED)

    def test_high_capture_count_is_excluded(self) -> None:
        result = classify(
            "https://www.record.pt/futebol/detalhe/pagina-persistente",
            "Futebol - Jornal Record",
            captures=500,
        )
        self.assertFalse(result.is_artigo)
        self.assertEqual(result.reason, REASON_CAPTURES_OUTLIER)

    def test_capture_count_at_threshold_is_still_artigo(self) -> None:
        result = classify(
            "https://www.record.pt/futebol/detalhe/no-limiar",
            "No limiar - Jornal Record",
            captures=100,
        )
        self.assertTrue(result.is_artigo)
        self.assertEqual(result.reason, REASON_ARTIGO)


class ClassifyCorpusTests(OfflineTestCase):
    """Testa classify_corpus() sobre CSV sintéticos, incluindo a normalização http/https."""

    def test_scheme_variants_merge_into_single_canonical_result(self) -> None:
        captures_csv = self.root / "corpus_phase1_captures.csv"
        history_csv = self.root / "corpus_phase2_history.csv"

        write_csv(captures_csv, PHASE1_FIELDS, [
            {
                "original_url": "http://www.record.pt/multimedia/videos/detalhe/exemplo.html",
                "tstamp": "20170702024006", "title": "Vídeo de exemplo - Jornal Record",
                "facets": "modalidade", "queries": "futebol",
                "num_queries_matched": "1", "divergent": "False",
            },
            {
                "original_url": "https://www.record.pt/multimedia/videos/detalhe/exemplo.html",
                "tstamp": "20170702024006", "title": "Vídeo de exemplo - Jornal Record",
                "facets": "modalidade", "queries": "andebol",
                "num_queries_matched": "1", "divergent": "False",
            },
        ])
        write_csv(history_csv, PHASE2_FIELDS, [
            {
                "original_url": "http://www.record.pt/multimedia/videos/detalhe/exemplo.html",
                "captures": "162", "estimated_total": "162",
                "requests_made": "4", "error": "",
            },
            {
                "original_url": "https://www.record.pt/multimedia/videos/detalhe/exemplo.html",
                "captures": "162", "estimated_total": "162",
                "requests_made": "4", "error": "",
            },
        ])

        results = classify_corpus(captures_csv, history_csv)

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].original_url,
            "https://www.record.pt/multimedia/videos/detalhe/exemplo.html",
        )
        self.assertEqual(results[0].captures, 162)
        self.assertFalse(results[0].is_artigo)
        self.assertEqual(results[0].reason, REASON_CAPTURES_OUTLIER)

    def test_mixed_corpus_classifies_each_category(self) -> None:
        captures_csv = self.root / "captures.csv"
        history_csv = self.root / "history.csv"

        write_csv(captures_csv, PHASE1_FIELDS, [
            {
                "original_url": "https://www.record.pt/futebol/detalhe/noticia-real",
                "tstamp": "20180101000000", "title": "Notícia real - Jornal Record",
                "facets": "modalidade", "queries": "futebol",
                "num_queries_matched": "1", "divergent": "False",
            },
            {
                "original_url": "https://www.record.pt/sabermais/jogador-exemplo",
                "tstamp": "20180101000000", "title": "Saber Mais: Jogador Exemplo",
                "facets": "atleta", "queries": "Jogador Exemplo",
                "num_queries_matched": "1", "divergent": "False",
            },
            {
                "original_url": "http://www.record.pt/Futebol/interior.aspx?content_id/x3d1",
                "tstamp": "20170101000000", "title": "Object moved",
                "facets": "modalidade", "queries": "futebol",
                "num_queries_matched": "1", "divergent": "False",
            },
        ])
        write_csv(history_csv, PHASE2_FIELDS, [
            {
                "original_url": "https://www.record.pt/futebol/detalhe/noticia-real",
                "captures": "3", "estimated_total": "3",
                "requests_made": "1", "error": "",
            },
            {
                "original_url": "https://www.record.pt/sabermais/jogador-exemplo",
                "captures": "250", "estimated_total": "250",
                "requests_made": "5", "error": "",
            },
            {
                "original_url": "http://www.record.pt/Futebol/interior.aspx?content_id/x3d1",
                "captures": "2", "estimated_total": "2",
                "requests_made": "1", "error": "",
            },
        ])

        results = {r.original_url: r for r in classify_corpus(captures_csv, history_csv)}

        self.assertEqual(len(results), 3)
        self.assertTrue(
            results["https://www.record.pt/futebol/detalhe/noticia-real"].is_artigo
        )
        self.assertFalse(
            results["https://www.record.pt/sabermais/jogador-exemplo"].is_artigo
        )
        self.assertEqual(
            results["https://www.record.pt/sabermais/jogador-exemplo"].reason,
            REASON_SABERMAIS,
        )
        self.assertFalse(
            results["http://www.record.pt/Futebol/interior.aspx?content_id/x3d1"].is_artigo
        )
        self.assertEqual(
            results["http://www.record.pt/Futebol/interior.aspx?content_id/x3d1"].reason,
            REASON_OBJECT_MOVED,
        )


if __name__ == "__main__":
    unittest.main()
