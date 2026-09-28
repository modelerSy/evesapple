from backend.app.models import Category, ExtractRequest

def test_extract_request_accepts_modes():
    assert ExtractRequest(category=Category.ADVERTISEMENT, content="4주 후 37% 개선").category == Category.ADVERTISEMENT
