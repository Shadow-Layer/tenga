from src.main import app
from src.swagger_ui_custom import get_swagger_ui_with_guide


def test_public_api_docs_do_not_disclose_demo_credentials():
    response = get_swagger_ui_with_guide(app)

    assert response.status_code == 200
    html = response.body.decode()
    assert "demo credentials:" not in html.lower()
    assert "teststore.com" not in html.lower()
