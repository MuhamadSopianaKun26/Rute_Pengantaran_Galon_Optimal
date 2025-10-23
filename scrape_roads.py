import os
import yaml
import requests
import osmnx as ox
import geopandas as gpd
import pandas as pd
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import tkinter as tk
from tkinter import simpledialog, messagebox
import folium
from folium import GeoJson
import networkx as nx
from branca.element import MacroElement, Figure, Element
import hashlib, json

class StableCircleMarker(folium.CircleMarker):
    def __init__(self, *args, unique_id=None, intersection=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._unique_id = unique_id
        self.intersection = intersection

    def get_name(self):
        if self._unique_id is not None:
            return f"circle_marker_{hashlib.md5(str(self._unique_id).encode()).hexdigest()}"
        return super().get_name()

    def add_to(self, parent):
        self._name = self.get_name()
        parent.add_child(self)
        return self

    def render(self, **kwargs):
        """Render bawaan Folium + injeksi metadata intersection."""
        MacroElement.render(self, **kwargs)

        # --- cari figure global yang menampung peta ---
        fig = None
        p = getattr(self, "_parent", None)
        while p is not None:
            if isinstance(p, Figure):
                fig = p
                break
            p = getattr(p, "_parent", None)

        # --- injeksikan JS tambahan ke figure ---
        if fig is not None and self.intersection is not None:
            meta_js = f"""
            {self.get_name()}._intersection = {json.dumps(self.intersection)};
            """
            fig.header.add_child(Element(f"<script>{meta_js}</script>"))

        return self
    
# --- Load config.yaml ---
with open("project/config.yaml", "r") as file:
    config = yaml.safe_load(file)

LOCATION = config.get("location", "Ciwaruga, Indonesia")
DISTANCE = config.get("distance", 1000)
NETWORK_TYPE = config.get("network_type", "drive")

# --- Check Internet Connection ---
try:
    requests.get("https://www.google.com", timeout=3)
except requests.RequestException:
    print("Tidak ada koneksi internet.")
    exit()

# --- Geocoding alamat ke koordinat ---
print(f"Mencari koordinat untuk: {LOCATION}")
geolocator = Nominatim(user_agent="geoapp")
location = geolocator.geocode(LOCATION)

if not location:
    print("Lokasi tidak ditemukan.")
    exit()

point = (location.latitude, location.longitude)
print(f"Koordinat: {point}")

# --- Ambil jaringan jalan ---
print("Mengambil jaringan jalan dari OpenStreetMap...")
G = ox.graph_from_point(point, dist=DISTANCE, network_type=NETWORK_TYPE)

# Konversi ke GeoDataFrame
nodes, edges = ox.graph_to_gdfs(G)

print("\nMembuat nama unik untuk setiap edge (jalan)...")

edge_name_counter = {}
unique_edge_names = []

for name in edges['name']:
    if isinstance(name, list):
        # Ambil nama pertama dari list
        name = name[0] if name else "Jalan Tanpa Nama"

    if pd.isna(name):
        base_name = "Jalan Tanpa Nama"
    else:
        base_name = str(name)

    if base_name not in edge_name_counter:
        edge_name_counter[base_name] = 1
        unique_edge_names.append(base_name)
    else:
        new_name = f"{base_name} {edge_name_counter[base_name]}"
        edge_name_counter[base_name] += 1
        unique_edge_names.append(new_name)

edges['unique_name'] = unique_edge_names

# --- Simpan Edge sebagai GeoJSON dan Shapefile ---
out_folder = "output"
os.makedirs(out_folder, exist_ok=True)
edges_roads = edges[['unique_name', 'geometry']].copy()
edges_roads.rename(columns={'unique_name': 'road_name'}, inplace=True)
edges_roads.to_file(os.path.join(out_folder, "road_names.geojson"), driver="GeoJSON")
print("✅ File 'road_names.geojson' berhasil disimpan.")

# --- Simpan Node sebagai GeoJSON dan Shapefile ---
edges.to_file(os.path.join(out_folder, "roads.geojson"), driver="GeoJSON")
edges.to_file(os.path.join(out_folder, "roads.shp"))
print("\n✅ Data mentah disimpan di folder 'output'.")  

# --- BAGIAN BARU: MEMBUAT NAMA KUSTOM UNTUK SIMPANG ---

print("\nMembuat nama kustom untuk setiap simpang...")

# Identifikasi node simpang (derajat >= 3)
intersections = [node for node, degree in G.degree() if degree >= 3]
nodes_intersections = nodes.loc[intersections].copy() # Gunakan .copy() untuk menghindari SettingWithCopyWarning

# Fungsi untuk mendapatkan nama jalan yang bertemu di sebuah node
def get_intersection_name(node_id, edges_gdf):
    """
    Mendapatkan nama jalan yang bertemu di sebuah node simpang.
    """
    # PERBAIKAN: Gunakan .index.get_level_values() untuk mengakses 'u' dan 'v' dari index
    connected_edges = edges_gdf[
        (edges_gdf.index.get_level_values('u') == node_id) | 
        (edges_gdf.index.get_level_values('v') == node_id)
    ]
    
    # Ambil nama jalan unik, bersihkan dari None atau list kosong
    road_names = set()
    for name in connected_edges['name'].dropna():
        if isinstance(name, list):
            road_names.update(name)
        else:
            road_names.add(name)
            
    if not road_names:
        return "Simpang Tanpa Nama"
    
    # Gabungkan nama jalan yang unik dan sudah diurutkan
    return " & ".join(sorted(list(road_names)))

# Terapkan fungsi ke setiap simpang untuk membuat kolom nama baru
nodes_intersections['intersection_name'] = nodes_intersections.index.map(lambda node_id: get_intersection_name(node_id, edges))


# --- MODIFIKASI: Ubah nama persimpangan jalan jika terdapat nama persimpangan yang sama ---
name_counter = {}
new_names = []

for name in nodes_intersections["intersection_name"]:
    if pd.isna(name):
        new_names.append(name)
        continue

    if name not in name_counter:
        name_counter[name] = 1
        new_names.append(name)
    else:
        new_name = f"{name}{name_counter[name]}"
        name_counter[name] += 1
        new_names.append(new_name)

nodes_intersections["intersection_name"] = new_names


# ===================================================================
# --- MEMBUAT PETA INTERAKTIF DENGAN INFORMASI BARU ---
# ===================================================================
print("\nMembuat peta interaktif dengan nama simpang dan bobot jalan...")

m = folium.Map(location=point, zoom_start=15, tiles="cartodbpositron")

# --- MODIFIKASI: Tambahkan jalan satu per satu untuk tooltip kustom ---
for _, row in edges.iterrows():
    # Ambil nama jalan (bisa berupa list, kita ambil yang pertama jika list)
    road_name = row['unique_name']
    if isinstance(road_name, list):
        road_name = road_name[0]
    if pd.isna(road_name):
        road_name = "Jalan Tanpa Nama"

    # Ambil panjang jalan (bobot) dalam meter
    road_length = row['length']

    # Buat layer GeoJson untuk jalan ini
    road_layer = folium.GeoJson(
        row['geometry'],
        style_function=lambda x: {'color': 'grey', 'weight': 3}
    )
    # Tambahkan tooltip yang menampilkan nama dan panjang jalan
    road_layer.add_child(
        folium.Tooltip(f"<b>{road_name}</b><br>Panjang: {road_length:.2f} m")
    ).add_to(m)


# --- MODIFIKASI: Update node simpang di peta dengan nama baru ---
for idx, row in nodes_intersections.iterrows():
    # Gunakan nama dari kolom baru 'intersection_name'
    tooltip_text = f"<b>{row['intersection_name']}</b><br>ID: {idx}"

    intersection_data = row.to_dict()
    for key, val in intersection_data.items():
        if isinstance(val, (pd.Series, pd.DataFrame, gpd.GeoSeries, gpd.GeoDataFrame)):
            intersection_data[key] = str(val)
        elif isinstance(val, (Point,)):
            intersection_data[key] = (val.x, val.y)

    hashed_name = "circle_marker_" + hashlib.md5(str(idx).encode()).hexdigest()
    
    marker = StableCircleMarker(
        location=(row['y'], row['x']),
        radius=5,
        color='#1f78b4',
        fill=True,
        fill_color='#1f78b4',
        fill_opacity=0.8,
        tooltip=f"<b>{row['intersection_name']}</b><br>ID: {idx}",
        unique_id=idx,
        intersection=intersection_data["intersection_name"]

    )
    marker.add_to(m)


# Modifikasi agar nama circle_marker menggunakan hashing dari idx (osmid kalau di geojson)

# Simpan node simpang ke file geojson
nodes_intersections.to_file(os.path.join(out_folder, "intersections_named.geojson"), driver="GeoJSON")

# Simpan peta sebagai file HTML
map_file = os.path.join(out_folder, "road_map_detailed.html")
m.save(map_file)

print(f"\n✅ Peta interaktif disimpan sebagai: {map_file}")
print("Silakan buka file tersebut di browser.")