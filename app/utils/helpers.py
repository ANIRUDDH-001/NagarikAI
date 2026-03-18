from bs4 import BeautifulSoup

def clean_html(raw_html: str) -> str:
    """
    Removes HTML tags from a text corpus.
    Useful for cleaning scraped context before sending it to an LLM.
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def sanitize_phone_number(phone: str) -> str:
    """
    Basic phone number sanitation logic.
    """
    return "".join(filter(str.isdigit, phone))
