# perbaiki_klasifikasi.py
import geopandas as gpd
import pandas as pd
import sys
from pathlib import Path

# === CONFIG ===
# Isi dengan nama file input yang kamu punya (hasil klasifikasi awal).
# Jika kamu belum punya intersections_with_region.geojson,
# ganti ke intersections_clean_fixed.geojson (input awal tanpa region).
INPUT = "intersections_named_final.geojson"   # atau "intersections_clean_fixed.geojson"
OUTPUT = "intersections_area_fixed.geojson"

# Rule-based keyword -> region overrides (priority order: top ke bawah)
# Tambahkan / sesuaikan kata kunci jika perlu.
KEYWORD_RULES = [
    ("geger kalong", "Gerlong"),
    ("geger", "Gerlong"),
    ("geg er", "Gerlong"),
    ("picung", "Gerlong"),          # some local names connecting to Geger Kalong
    ("ciwaruga", "Ciwaruga"),
    ("sariasih", "Sariasih"),       # jika mau Sariasih terpisah
    ("sarkasih", "Gerlong"),
    ("setrasari", "Sarijadi"),
    ("sarijadi", "Sarijadi"),
    ("sarimanah", "Sarimanah"),
    ("sukahaji", "Sarijadi"),       # contoh nama jalan yang dekat Sarijadi
    # tambahkan kata kunci lain sesuai yang kamu temukan
]

def load_gdf(path):
    if not Path(path).exists():
        print(f"[ERROR] File input tidak ditemukan: {path}")
        sys.exit(1)
    gdf = gpd.read_file(path)
    # Pastikan ada field intersection_name
    if 'intersection_name' not in gdf.columns:
        print("[WARN] Kolom 'intersection_name' tidak ditemukan. Cek kolom yang ada:", gdf.columns.tolist())
    return gdf.to_crs(epsg=4326)

def apply_rules(gdf):
    # create copy for before/after comparison
    gdf = gdf.copy()
    before = gdf['region_name'].copy() if 'region_name' in gdf.columns else pd.Series([None]*len(gdf), index=gdf.index)

    # ensure intersection_name exists
    if 'intersection_name' not in gdf.columns:
        print("[ERROR] Kolom 'intersection_name' wajib ada. Proses dihentikan.")
        sys.exit(1)

    def override_region(name, current):
        if not isinstance(name, str):
            return current
        n = name.lower()
        for kw, region in KEYWORD_RULES:
            if kw in n:
                return region
        return current

    gdf['region_name_fixed'] = gdf.apply(lambda r: override_region(r.get('intersection_name', ''), r.get('region_name', None)), axis=1)

    changed_idx = gdf[gdf.get('region_name', None) != gdf['region_name_fixed']].index
    changed = pd.DataFrame({
        'osmid': gdf.loc[changed_idx, 'osmid'],
        'intersection_name': gdf.loc[changed_idx, 'intersection_name'],
        'before': gdf.loc[changed_idx, 'region_name'],
        'after': gdf.loc[changed_idx, 'region_name_fixed']
    })

    # commit fixed region_name
    gdf['region_name'] = gdf['region_name_fixed']
    gdf = gdf.drop(columns=['region_name_fixed'])

    return gdf, before.value_counts(dropna=False), gdf['region_name'].value_counts(dropna=False), changed

def main():
    print("Membaca file:", INPUT)
    gdf = load_gdf(INPUT)
    print("Total titik:", len(gdf))

    gdf_fixed, counts_before, counts_after, changed = apply_rules(gdf)

    # Save output
    gdf_fixed.to_file(OUTPUT, driver="GeoJSON")
    print(f"\nSimpan hasil perbaikan ke: {OUTPUT}\n")

    print("Ringkasan jumlah per region (SEBELUM):")
    print(counts_before.to_string(), "\n")
    print("Ringkasan jumlah per region (SETELAH):")
    print(counts_after.to_string(), "\n")

    print(f"Total perubahan label yang dilakukan: {len(changed)}")
    if len(changed) > 0:
        print("Contoh 20 perubahan (osmid, intersection_name, before -> after):")
        print(changed.head(20).to_string(index=False))
    else:
        print("Tidak ada perubahan berdasarkan rule keyword yang diberikan.")

    print("\nSelesai. Periksa file output atau buka contoh perubahan di atas.")

if __name__ == '__main__':
    main()
