
import re
import pandas as pd

# ============================================================
# REFERENSI KODE WILAYAH PROVINSI ACEH
# Sumber: daftar referensi kode wilayah yang diberikan
# ============================================================

KODE_WILAYAH_ACEH = {
    "1101": "Simeulue",
    "1102": "Aceh Singkil",
    "1103": "Aceh Selatan",
    "1104": "Aceh Tenggara",
    "1105": "Aceh Timur",
    "1106": "Aceh Tengah",
    "1107": "Aceh Barat",
    "1108": "Aceh Besar",
    "1109": "Pidie",
    "1110": "Bireuen",
    "1111": "Aceh Utara",
    "1112": "Aceh Barat Daya",
    "1113": "Gayo Lues",
    "1114": "Aceh Tamiang",
    "1115": "Nagan Raya",
    "1116": "Aceh Jaya",
    "1117": "Bener Meriah",
    "1118": "Pidie Jaya",
    "1171": "Banda Aceh",
    "1172": "Sabang",
    "1173": "Langsa",
    "1174": "Lhokseumawe",
    "1175": "Subulussalam",
}

# Daftar kabupaten/kota untuk dashboard
ACEH_REGENCIES = list(KODE_WILAYAH_ACEH.values())


# ============================================================
# EKSTRAK KODE WILAYAH DARI KODE IDENTITAS
# ============================================================

def extract_kode_wilayah(row):

    if not hasattr(row, "get"):
        return None

    # Prioritaskan kolom Kode Identitas
    kandidat_kolom = [
        "Kode Identitas",
        "kode identitas",
        "Identitas",
        "Identity Code",
        "ID Assignment",
    ]

    nilai = None

    for kolom in kandidat_kolom:
        value = row.get(kolom)

        if value is not None and not pd.isna(value):
            nilai = str(value).strip()
            if nilai:
                break

    if not nilai:
        return None

    # Ambil tepat empat digit pertama
    match = re.match(r"^(\d{4})", nilai)

    if not match:
        return None

    kode = match.group(1)

    if kode in KODE_WILAYAH_ACEH:
        return kode

    return None


# ============================================================
# MENENTUKAN KABUPATEN/KOTA
# ============================================================

def infer_wilayah(row):

    # Ambil kode yang sudah diekstrak
    kode = row.get("Kode Wilayah")

    if kode is None or pd.isna(kode):
        kode = extract_kode_wilayah(row)

    if kode is None:
        return "BELUM TERIDENTIFIKASI"

    kode = str(kode).strip()

    return KODE_WILAYAH_ACEH.get(
        kode,
        "BELUM TERIDENTIFIKASI"
    )
