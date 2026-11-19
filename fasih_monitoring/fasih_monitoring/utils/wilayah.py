ACEH_REGENCIES = [
    "Aceh Barat", "Aceh Barat Daya", "Aceh Besar", "Aceh Jaya", "Aceh Selatan",
    "Aceh Singkil", "Aceh Tamiang", "Aceh Tengah", "Aceh Tenggara", "Aceh Timur",
    "Aceh Utara", "Bener Meriah", "Bireuen", "Gayo Lues", "Nagan Raya", "Pidie",
    "Pidie Jaya", "Simeulue", "Kota Banda Aceh", "Kota Langsa", "Kota Lhokseumawe",
    "Kota Sabang", "Kota Subulussalam"
]

ALIASES = {
    "kabupaten aceh barat":"Aceh Barat", "kab aceh barat":"Aceh Barat",
    "kabupaten aceh barat daya":"Aceh Barat Daya", "kabupaten aceh besar":"Aceh Besar",
    "kabupaten aceh jaya":"Aceh Jaya", "kabupaten aceh selatan":"Aceh Selatan",
    "kabupaten aceh singkil":"Aceh Singkil", "kabupaten aceh tamiang":"Aceh Tamiang",
    "kabupaten aceh tengah":"Aceh Tengah", "kabupaten aceh tenggara":"Aceh Tenggara",
    "kabupaten aceh timur":"Aceh Timur", "kabupaten aceh utara":"Aceh Utara",
    "kabupaten bener meriah":"Bener Meriah", "kabupaten bireuen":"Bireuen",
    "kabupaten gayo lues":"Gayo Lues", "kabupaten nagan raya":"Nagan Raya",
    "kabupaten pidie":"Pidie", "kabupaten pidie jaya":"Pidie Jaya",
    "kabupaten simeulue":"Simeulue", "banda aceh":"Kota Banda Aceh",
    "kota banda aceh":"Kota Banda Aceh", "langsa":"Kota Langsa", "kota langsa":"Kota Langsa",
    "lhokseumawe":"Kota Lhokseumawe", "kota lhokseumawe":"Kota Lhokseumawe",
    "sabang":"Kota Sabang", "kota sabang":"Kota Sabang",
    "subulussalam":"Kota Subulussalam", "kota subulussalam":"Kota Subulussalam"
}

def normalize_wilayah(value):
    if value is None:
        return "BELUM TERIDENTIFIKASI"
    text = " ".join(str(value).strip().lower().replace(".", " ").split())
    if not text or text in ["nan", "none", "-"]:
        return "BELUM TERIDENTIFIKASI"
    if text in ALIASES:
        return ALIASES[text]
    for name in ACEH_REGENCIES:
        if text == name.lower():
            return name
    return "BELUM TERIDENTIFIKASI"
