"""
delivery_coloring.py

Modul untuk:
- memuat graf peta dari OSMnx + membaca GeoJSON (fungsi muat_osm_dan_geojson)
- membuat graf order dari JSON (fungsi build_order_graph_from_json)
- menampilkan graf (fungsi display_graph)
- melakukan "graph coloring" dengan batas kapasitas (fungsi color_graph_with_capacity)
- visualisasi hasil coloring (visualize_coloring)

Dependencies: networkx, osmnx, geopandas, matplotlib, json
"""

import json
import os
from typing import Tuple, Dict, List, Any, Union

import networkx as nx
import matplotlib.pyplot as plt

# optional libs for map loading
try:
    import osmnx as ox
    import geopandas as gpd
except Exception:
    ox = None
    gpd = None
    # Modul tetap berguna tanpa osmnx/geopandas untuk bagian graph order


# ----------------------------
# Fungsi 1: muat data peta + geojson
# ----------------------------
def muat_osm_dan_geojson(point: Tuple[float, float],
                         distance: int = 1000,
                         network_type: str = "drive",
                         path_ke_geojson: str = None) -> Tuple[Any, Any]:
    """
    Memuat graf peta dari OSMnx dan (opsional) GeoJSON. Mengembalikan tuple (G, gdf)
    Jika osmnx/gpd tidak terinstal, mengembalikan (None,None) dengan pesan.
    """
    if ox is None or gpd is None:
        print("Peringatan: osmnx atau geopandas tidak tersedia di environment Anda.")
        return None, None

    print("Memuat graf dari OpenStreetMap (osmnx)...")
    G = ox.graph_from_point(point, dist=distance, network_type=network_type)
    print("Graf peta berhasil dimuat.")

    gdf = None
    if path_ke_geojson:
        if not os.path.exists(path_ke_geojson):
            print(f"File GeoJSON tidak ditemukan: {path_ke_geojson}")
        else:
            gdf = gpd.read_file(path_ke_geojson)
            print("GeoJSON berhasil dimuat.")

    return G, gdf


# ----------------------------
# Fungsi 2: tampilkan graph (generic)
# ----------------------------
def display_graph(G: nx.Graph,
                  pos: Dict = None,
                  node_color_map: Dict[Any, int] = None,
                  title: str = "Graph",
                  figsize: Tuple[int, int] = (10, 8),
                  with_labels: bool = True):
    """
    Menampilkan graf networkx dengan matplotlib.
    node_color_map: dict node -> color_id (int). Jika None, gunakan warna default.
    """
    plt.figure(figsize=figsize)

    if pos is None:
        pos = nx.spring_layout(G, seed=42)

    if node_color_map is None:
        nx.draw(G, pos=pos, with_labels=with_labels, node_size=600)
        plt.title(title)
        plt.show()
        return

    # ubah color id ke warna matplotlib via colormap
    color_ids = [node_color_map.get(n, -1) for n in G.nodes()]
    # map -1 -> gray
    import matplotlib.cm as cm
    import numpy as np
    maxid = max(color_ids) if color_ids else 0
    if maxid <= 0:
        cmap = cm.get_cmap('tab20', 2)
    else:
        cmap = cm.get_cmap('tab20', maxid + 1)
    colors = []
    for cid in color_ids:
        if cid == -1:
            colors.append("#cccccc")
        else:
            # normalize cid to colormap index
            colors.append(cmap(cid % 20))
    nx.draw(G, pos=pos, with_labels=with_labels, node_size=700, node_color=colors)
    plt.title(title)
    plt.show()


# ----------------------------
# Fungsi 3: build graph dari JSON (orders)
# ----------------------------
def build_order_graph_from_json(input_data: Union[str, List[dict]],
                                galon_cap: int = 4,
                                kardus_cap: int = 2) -> nx.Graph:
    """
    Membangun graf order dari file JSON atau objek list-of-dict.
    JSON format contoh (list):
    [
      {"id": "A", "galon": 1, "kardus": 0},
      {"id": "B", "galon": 2, "kardus": 2},
      ...
    ]

    Logika edge:
    - Tambahkan edge (u,v) jika galon_u + galon_v > galon_cap OR kardus_u + kardus_v > kardus_cap
    - Jika node sendirian melebihi kapasitas (galon>galon_cap or kardus>kardus_cap),
      node diberi atribut 'solo'=True dan *dihubungkan ke semua* node lain untuk mencegah
      bergabung (opsional: juga bisa dibiarkan tanpa edge karena coloring akan menangani solo).
    """
    if isinstance(input_data, str):
        if not os.path.exists(input_data):
            raise FileNotFoundError(f"{input_data} tidak ditemukan.")
        with open(input_data, "r", encoding="utf-8") as f:
            orders = json.load(f)
    else:
        orders = input_data  # assume already list[dict]

    G = nx.Graph()
    # add nodes with attributes
    for o in orders:
        oid = str(o.get("id"))
        gal = int(o.get("galon", 0))
        kar = int(o.get("kardus", 0))
        solo = (gal > galon_cap) or (kar > kardus_cap)
        G.add_node(oid, galon=gal, kardus=kar, solo=solo)

    nodes = list(G.nodes(data=True))
    # create pairwise edges if pair exceeds capacity
    for i in range(len(nodes)):
        u, au = nodes[i][0], nodes[i][1]
        for j in range(i + 1, len(nodes)):
            v, av = nodes[j][0], nodes[j][1]
            if au['galon'] + av['galon'] > galon_cap or au['kardus'] + av['kardus'] > kardus_cap:
                G.add_edge(u, v)

    # for clarity: connect solo nodes to everyone to ensure they won't be grouped accidentally
    for n, attr in G.nodes(data=True):
        if attr.get('solo'):
            for m in G.nodes():
                if m != n:
                    G.add_edge(n, m)

    return G


# ----------------------------
# Fungsi 4: coloring with capacity constraints
# ----------------------------
def color_graph_with_capacity(G: nx.Graph,
                              galon_cap: int = 4,
                              kardus_cap: int = 2,
                              sort_key: str = "galon_then_kardus") -> Tuple[Dict[Any, int], Dict[int, dict]]:
    """
    Pewarnaan heuristik (Greedy FFD) yang memperhatikan:
    - Tidak boleh ada dua node bertetangga pada warna yang sama (conflict edges)
    - Total galon/kardus pada setiap warna tidak boleh melebihi kapasitas

    Mengembalikan:
    - coloring: dict node -> color_id (integer, 0..k-1)
    - bins: dict color_id -> {'nodes': [...], 'total_galon': int, 'total_kardus': int, 'solo': bool}
    """
    # prepare nodes list, sort descending (largest first) => FFD
    nodes_with_attr = [(n, d['galon'], d['kardus'], d.get('solo', False)) for n, d in G.nodes(data=True)]

    if sort_key == "galon_then_kardus":
        nodes_with_attr.sort(key=lambda t: (t[1], t[2]), reverse=True)
    elif sort_key == "sum":
        nodes_with_attr.sort(key=lambda t: (t[1] + t[2]), reverse=True)
    else:
        nodes_with_attr.sort(key=lambda t: (t[1], t[2]), reverse=True)

    coloring: Dict[Any, int] = {}
    bins: Dict[int, dict] = {}  # color_id -> metadata

    def can_place(node_id: str, bin_meta: dict) -> bool:
        # check conflict edges: node must not be adjacent to any node already in this bin
        for placed in bin_meta['nodes']:
            if G.has_edge(node_id, placed):
                return False
        # check capacity sums
        node_attr = G.nodes[node_id]
        if bin_meta['total_galon'] + node_attr['galon'] > galon_cap:
            return False
        if bin_meta['total_kardus'] + node_attr['kardus'] > kardus_cap:
            return False
        return True

    for node_id, gal, kar, solo in nodes_with_attr:
        if solo:
            # place in its own bin immediately
            cid = len(bins)
            bins[cid] = {'nodes': [node_id], 'total_galon': gal, 'total_kardus': kar, 'solo': True}
            coloring[node_id] = cid
            continue

        placed = False
        # try existing bins in order (First-Fit)
        for cid, meta in bins.items():
            if meta.get('solo', False):
                continue  # don't try to place into solo bins
            if can_place(node_id, meta):
                meta['nodes'].append(node_id)
                meta['total_galon'] += gal
                meta['total_kardus'] += kar
                coloring[node_id] = cid
                placed = True
                break

        if not placed:
            # open new bin
            cid = len(bins)
            bins[cid] = {'nodes': [node_id], 'total_galon': gal, 'total_kardus': kar, 'solo': False}
            coloring[node_id] = cid

    return coloring, bins


# ----------------------------
# Visualisasi hasil pewarnaan (graph + bins summary)
# ----------------------------
def visualize_coloring(G: nx.Graph,
                       coloring: Dict[Any, int],
                       galon_cap: int = 4,
                       kardus_cap: int = 2,
                       figsize: Tuple[int, int] = (12, 9)):
    """
    Menampilkan graf dengan warna sesuai coloring, dan menampilkan ringkasan bins.
    """
    # draw graph colored
    pos = nx.spring_layout(G, seed=71)
    display_graph(G, pos=pos, node_color_map=coloring, title="Delivery Conflict Graph (colored)", figsize=figsize)

    # print bins summary
    bins = {}
    for n, cid in coloring.items():
        bins.setdefault(cid, []).append(n)

    print("\nRingkasan pengiriman per slot (warna):")
    for cid in sorted(bins.keys()):
        total_g = sum(G.nodes[n]['galon'] for n in bins[cid])
        total_k = sum(G.nodes[n]['kardus'] for n in bins[cid])
        solo_flag = any(G.nodes[n].get('solo', False) for n in bins[cid])
        print(f" Slot {cid}: Nodes = {bins[cid]}")
        print(f"   Total galon = {total_g} / {galon_cap}, Total kardus = {total_k} / {kardus_cap}, solo_flag={solo_flag}")
    print("Catatan: jika slot menunjukkan total melebihi kapasitas, berarti terjadi bug pada heuristik.")

def load_orders(schedule, json_file="order_data.json"):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = []
    
    for order in data:
        # Filter sesuai schedule dan status
        if str(order.get("schedule", "")).strip() == schedule and order.get("status") == "sedang_disiapkan":
            galon_qty = 0
            box_qty = 0
            
            # Loop item dalam pesanan
            for item in order.get("items", []):
                name = item.get("name", "").lower()
                qty = item.get("qty", 0)

                # deteksi galon
                if "galon" in name:
                    galon_qty += qty
                # deteksi box/kardus
                if "box" in name or "kardus" in name:
                    box_qty += qty

            result.append({
                "name": order.get("customer_name", ""),
                "galon": galon_qty,
                "box": box_qty
            })

    return result


# ----------------------------
# Contoh penggunaan singkat
# ----------------------------
if __name__ == "__main__":
    # contoh orders (dari pertanyaan)
    orders = [
        {"id": "A", "galon": 1, "kardus": 1},
        {"id": "B", "galon": 1, "kardus": 1},
        {"id": "C", "galon": 1, "kardus": 1},
        {"id": "D", "galon": 2, "kardus": 2},
        {"id": "E", "galon": 1, "kardus": 1},
        {"id": "F", "galon": 1, "kardus": 0},
        {"id": "G", "galon": 2, "kardus": 1},
        {"id": "H", "galon": 1, "kardus": 0},
        {"id": "I", "galon": 3, "kardus": 2},
        {"id": "J", "galon": 2, "kardus": 0},
    ]

    G_orders = build_order_graph_from_json(orders, galon_cap=4, kardus_cap=2)
    coloring, bins = color_graph_with_capacity(G_orders, galon_cap=4, kardus_cap=2)
    print("Coloring result:", coloring)
    visualize_coloring(G_orders, coloring, galon_cap=4, kardus_cap=2)
