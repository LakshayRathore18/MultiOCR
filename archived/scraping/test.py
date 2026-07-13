import re

def extract_devanagari(text: str):
    """
    Keeps ONLY Devanagari Unicode characters (U+0900–U+097F) and spaces.
    Removes everything else.
    """
    # Remove non-Devanagari characters
    cleaned = re.sub(r"[^\u0900-\u097F\s]", " ", text)

    # Normalize whitespace and return tokens
    return cleaned.split()


if __name__ == "__main__":
    text = """
    प्रयोजनवदायुर्वेदोपादानम्|
    युगनियतमायुः,
    तन्नातिबलवता
    नियमितं;
    रसायनप्रयोगात्तद्बाधनं
    दृष्टत्वादनुमन्यन्ते,
    स्वस्थहितातुरहितचिकित्साभ्याम्|
    शास्त्रकारेण
    स्वयमेव
    प्रपञ्चेन
    निर्लोचनीय
    प्रतन्यते||३||
    . ‘चैवमाचार्यस्य’ इति पा.|
    . ‘बलवत्वात्’ इति पा.
    """

    words = extract_devanagari(text)
    print(words)
