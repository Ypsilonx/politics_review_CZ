"""Test změnových požadavků Sledovaných: ochrana proti CSRF a přesměrování jen v rámci aplikace."""

import pytest
from fastapi.testclient import TestClient

from politika import config
from politika.db.connection import get_connection
from politika.web.app import create_app


@pytest.fixture
def klient(tmp_path, monkeypatch):
    """Aplikace nad prázdnou dočasnou databází (skutečná data se nedotknou)."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    get_connection(config.DB_PATH).close()
    return TestClient(create_app(), base_url="http://testserver")


def _pocet(conn_cesta) -> int:
    conn = get_connection(conn_cesta)
    try:
        return conn.execute("SELECT COUNT(*) FROM sledovany").fetchone()[0]
    finally:
        conn.close()


def test_cizi_stranka_nesmi_menit_sledovane(klient):
    data = {"typ": "poslanec", "id": "2095", "zpet": "/sledovani"}
    odpoved = klient.post("/sledovani/pridat", data=data,
                          headers={"Origin": "http://zla-stranka.example"}, follow_redirects=False)
    assert odpoved.status_code == 403
    assert _pocet(config.DB_PATH) == 0


def test_vlastni_stranka_prida_a_presmeruje_jen_v_aplikaci(klient):
    data = {"typ": "poslanec", "id": "2095", "zpet": "//zla-stranka.example/"}
    odpoved = klient.post("/sledovani/pridat", data=data,
                          headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert odpoved.status_code == 303
    assert odpoved.headers["location"] == "/sledovani"
    assert _pocet(config.DB_PATH) == 1
