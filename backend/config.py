GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
API_KEY = 'AIzaSyCuKsGvqGPO_WTv8doiBp4yF5k9hqHCRuc'
if not GOOGLE_BOOKS_URL or not API_KEY:
    raise RuntimeError("Не задані GOOGLE_BOOKS_URL або API_KEY")
