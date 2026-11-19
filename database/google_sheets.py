"""Optional Google Sheets connector.

Enable only after the organization provides an authorized service-account setup.
Do not commit credentials. The initial application uses SQLite so it can run locally
without requiring service-account secrets.
"""

class GoogleSheetsNotConfigured(RuntimeError):
    pass

def connect():
    raise GoogleSheetsNotConfigured(
        "Google Sheets belum dikonfigurasi. Siapkan service account resmi dan spreadsheet ID."
    )
