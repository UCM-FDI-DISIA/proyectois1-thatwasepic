import pytest


@pytest.mark.parametrize("path", ["/", "/login", "/register"])
def test_public_routes_ok(client, path):
    """Public pages should render successfully"""
    response = client.get(path)
    assert response.status_code == 200
    # Basic sanity: HTML structure should be present
    assert b"<html" in response.data


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard",
        "/perfil",
        "/estadisticas",
        "/salas-espera",
        "/coinflip",
        "/blackjack",
        "/ruleta",
        "/caballos",
        "/quiniela",
        "/tragaperras",
        "/admin",
        "/admin/usuarios",
        "/admin/estadisticas",
    ],
)
def test_protected_routes_redirect_to_login(client, path):
    """Protected pages should redirect anonymous users to login"""
    response = client.get(path)
    assert response.status_code in (301, 302)
    assert "/login" in response.headers.get("Location", "")


def test_missing_route_returns_404(client):
    """Unknown routes should respond with 404"""
    response = client.get("/ruta-que-no-existe")
    assert response.status_code == 404
