"""Smoke test real do primeiro vertical slice."""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from .arquivo_client import ArquivoClient


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    project_root = Path(__file__).resolve().parents[2]
    client = ArquivoClient(data_dir=project_root / "data" / "raw")

    try:
        search = client.search(
            query="Benfica",
            site_search="record.pt",
            from_date="2018",
            to_date="2020",
            max_items=20,
        )
    except (requests.RequestException, RuntimeError, OSError) as exc:
        logging.error("A pesquisa falhou: %s", exc)
        return 1

    downloads = client.download_extracted_texts(search.results)

    print("\nResumo")
    print(f"Resultados recebidos: {len(search.results)}")
    print(f"Textos descarregados com sucesso: {downloads.downloaded}")
    print(f"Textos que falharam: {downloads.failed}")
    print(f"Resultados sem link de texto: {downloads.without_link}")
    print(f"Pesquisas guardadas em: {client.searches_dir}")
    print(f"Textos guardados em: {client.texts_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
