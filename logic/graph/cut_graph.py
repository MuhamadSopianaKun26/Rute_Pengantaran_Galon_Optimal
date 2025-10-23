import textwrap
import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt

# =============================================================================
# BAGIAN SETUP AWAL (Cukup dijalankan sekali saat aplikasi pertama kali start)
# =============================================================================

def muat_data_peta_dan_lokasi(point, distance=1000, network_type="drive", path_ke_geojson="intersections_named_final.geojson"):
    """
    Memuat graf peta dari OSMnx DAN data lokasi penting dari file GeoJSON.
    Mengembalikan:
        G (networkx.MultiDiGraph) -- graf peta dari osmnx
        gdf_lokasi (GeoDataFrame) -- isi geojson (bila ada)
    """
    print("Memuat graf jaringan jalan dari OpenStreetMap...")
    try:
        G = ox.graph_from_point(point, dist=distance, network_type=network_type)
        print("[OK] Graf peta berhasil dimuat.")
    except Exception as e:
        print(f"Gagal memuat graf peta: {e}")
        return None, None

    try:
        gdf_lokasi = gpd.read_file(path_ke_geojson)
        print("[OK] Data lokasi penting (GeoJSON) berhasil dimuat.")
        print("Nama kolom yang tersedia di GeoJSON:", gdf_lokasi.columns)
    except Exception as e:
        print(f"Peringatan: gagal memuat GeoJSON ({e}). Melanjutkan tanpa gdf_lokasi.")
        gdf_lokasi = None

    return G, gdf_lokasi

# =============================================================================
# FUNGSI ANALISIS: CUT VERTEX & CUT EDGES
# =============================================================================

def analisis_titik_rawan(G):
    """
    Menganalisis graf (G bisa MultiDiGraph dari osmnx) untuk menemukan:
      - articulation points (cut vertices)
      - bridges / cut edges

    Catatan: networkx.articulation_points dan bridges bekerja pada graf undirected.
    """
    print("Menganalisis graf untuk menemukan cut vertex dan cut edge (bridge)...")
    # Konversi ke graf undirected sederhana untuk analisis struktur konektivitas
    G_und = nx.Graph()
    G_und.add_nodes_from(G.nodes(data=True))
    # Tambahkan sisi tanpa duplikasi; untuk edge attributes, kita hanya butuh struktur
    for u, v, _ in G.edges(keys=True):
        G_und.add_edge(u, v)

    try:
        cut_vertices = list(nx.articulation_points(G_und))
    except Exception as e:
        print(f"[Error] Saat mencari articulation points: {e}")
        cut_vertices = []

    try:
        bridges = list(nx.bridges(G_und))
    except Exception as e:
        print(f"[Error] Saat mencari bridges: {e}")
        bridges = []

    print(f"Ditemukan {len(cut_vertices)} cut vertex.")
    print(f"Ditemukan {len(bridges)} cut edges (bridges).")

    return cut_vertices, bridges

import networkx as nx

# =============================================================================
# FUNGSI HAPUS / CUT VERTEX DAN CUT EDGES
# =============================================================================

def hapus_cut_vertex(G, nodes):
    """
    Menghapus node cut vertex dari graph (copy-safe).

    Parameter:
    - G : nx.Graph (graph jalan)
    - nodes : iterable atau single node id

    Return:
    - G_mod : nx.Graph (graph baru tanpa node-node tersebut)
    """
    # buat salinan graph dulu agar tidak mengubah graph asli
    G_mod = G.copy()

    # jika single value, ubah menjadi list agar konsisten
    if not isinstance(nodes, (list, set, tuple)):
        nodes = [nodes]

    for n in nodes:
        if G_mod.has_node(n):
            G_mod.remove_node(n)

    return G_mod


def hapus_cut_edges(G, edges):
    """
    Menghapus cut edges (bridge) dari graph (copy-safe).

    Parameter:
    - G : nx.Graph (graph jalan)
    - edges : iterable of tuples (u, v) atau single tuple (u, v)

    Return:
    - G_mod : nx.Graph (graph baru tanpa edge-edge tersebut)
    """
    # buat salinan graph
    G_mod = G.copy()

    # single edge -> jadi list
    if isinstance(edges, tuple):
        edges = [edges]

    for (u, v) in edges:
        # karena graph tidak berarah, bisa cek dua arah
        if G_mod.has_edge(u, v):
            G_mod.remove_edge(u, v)
        elif G_mod.has_edge(v, u):
            G_mod.remove_edge(v, u)

    return G_mod


# =============================================================================
# VISUALISASI CUT VERTEX (separate plot)
# =============================================================================

def visualisasi_cut_vertex(G, cut_vertices, title_suffix=""):
    """
    Menampilkan graf peta dengan cut vertices di-highlight (Mode 1):
    - Semua jaringan tetap ditampilkan (background)
    - Cut vertices digambar merah lebih besar
    """
    if G is None:
        print("Graf tidak tersedia untuk visualisasi cut vertex.")
        return

    print("Membuat visualisasi Cut Vertex...")
    # Posisi simpul dari atribut x,y (OSMnx)
    pos = {n: (data['x'], data['y']) for n, data in G.nodes(data=True)}

    # Plot dasar peta dengan osmnx (menghasilkan fig, ax untuk overlay)
    fig, ax = ox.plot_graph(G, node_size=0, edge_linewidth=0.6, show=False, close=False)
    ax.set_title(f"Cut Vertices (Articulation Points) {title_suffix}")

    # Gambar semua simpul dengan ukuran kecil (sebagai konteks)
    try:
        nx.draw_networkx_nodes(G, pos, nodelist=list(G.nodes()), node_size=10, node_color='gray', alpha=0.6, ax=ax)
    except Exception:
        # fallback: jika graf memiliki node tanpa posisi, skip
        pass

    # Gambar cut vertices (jika ada)
    if cut_vertices:
        nx.draw_networkx_nodes(G, pos, nodelist=cut_vertices, node_size=80, node_color='red', alpha=0.9, ax=ax)
        # optional: label angka kecil di atas node
        # nx.draw_networkx_labels(G, pos, labels={n: str(n) for n in cut_vertices}, font_size=6, ax=ax)
    else:
        ax.text(0.5, 0.5, "Tidak ada cut vertex terdeteksi", transform=ax.transAxes, ha='center', va='center')

    plt.show()

# =============================================================================
# VISUALISASI CUT EDGES / BRIDGES (separate plot)
# =============================================================================

def visualisasi_cut_edges(G, bridges, title_suffix=""):
    """
    Menampilkan graf peta dengan cut edges (bridges) di-highlight (Mode 1):
    - Semua jaringan tetap ditampilkan (background)
    - Bridges digambar merah dan sedikit lebih tebal
    """
    if G is None:
        print("Graf tidak tersedia untuk visualisasi cut edges.")
        return

    print("Membuat visualisasi Cut Edges / Bridges...")
    pos = {n: (data['x'], data['y']) for n, data in G.nodes(data=True)}

    # Plot dasar peta
    fig, ax = ox.plot_graph(G, node_size=0, edge_linewidth=0.6, show=False, close=False)
    ax.set_title(f"Cut Edges / Bridges {title_suffix}")

    # Gambar semua edges sebagai konteks
    try:
        nx.draw_networkx_edges(G, pos, edgelist=list(G.edges()), width=0.6, alpha=0.5, ax=ax)
    except Exception:
        pass

    # Gambar bridges (edge list) jika ada
    if bridges:
        # Pastikan bridges ada dalam format list of tuples (u,v)
        bridgelist = [(u, v) for u, v in bridges]
        # Gambar dengan linewidth lebih besar dan warna merah
        nx.draw_networkx_edges(G, pos, edgelist=bridgelist, width=2.5, edge_color='red', ax=ax)
    else:
        ax.text(0.5, 0.5, "Tidak ada cut edge (bridge) terdeteksi", transform=ax.transAxes, ha='center', va='center')

    plt.show()

# =============================================================================
# SIMULASI (opsional) : menghapus simpul atau sisi lalu cek efek
# =============================================================================

def simulasi_putus_jalur(G, elemen_diputus):
    """
    Mensimulasikan dampak penghapusan simpul (int) atau sisi (tuple (u,v)).
    Memvisualisasikan graf hasil hapus.
    """
    if G is None:
        print("Graf tidak tersedia.")
        return

    if elemen_diputus is None:
        print("Tidak ada elemen untuk diputus.")
        return

    print(f"Mensimulasikan penghapusan elemen: {elemen_diputus}")
    G_copy = G.copy()

    if isinstance(elemen_diputus, (int, str)):
        if elemen_diputus not in G_copy:
            print(f"Simpul {elemen_diputus} tidak ditemukan.")
            return
        G_copy.remove_node(elemen_diputus)
        tipe = "Simpul"
    elif isinstance(elemen_diputus, tuple) and len(elemen_diputus) == 2:
        u, v = elemen_diputus
        if not G_copy.has_edge(u, v):
            print(f"Sisi {(u, v)} tidak ditemukan.")
            return
        # remove only one edge: for multigraph, remove_edge(u,v,key) but here we remove all u-v edges
        G_copy.remove_edges_from(list(G_copy.edges(u, data=True)))
        tipe = "Sisi"
    else:
        print("Input elemen tidak valid.")
        return

    # Analisis dampak
    G_und_copy = nx.Graph()
    G_und_copy.add_nodes_from(G_copy.nodes(data=True))
    for u, v, _ in G_copy.edges(keys=True):
        G_und_copy.add_edge(u, v)

    if nx.is_connected(G_und_copy):
        status = "Jaringan TETAP TERHUBUNG."
    else:
        status = f"Jaringan TERPUTUS menjadi {nx.number_connected_components(G_und_copy)} bagian."

    print("Hasil simulasi:", status)

    # Visualisasikan hasil
    fig, ax = ox.plot_graph(G_copy, node_size=10, edge_linewidth=0.8, show=False, close=False)
    ax.set_title(f"Dampak Penghapusan {tipe} {elemen_diputus}\n{status}")
    plt.show()

# =============================================================================
# MAIN: contoh pemakaian
# =============================================================================

if __name__ == "__main__":
    # Contoh: Koordinat pusat area (Bandung - ganti sesuai kebutuhan)
    lokasi_peta = (-6.872, 107.578)

    # Path ke file GeoJSON Anda (ganti dengan path sebenarnya)
    path_geojson = "intersections_area.geojson"

    # 1. Muat data
    graf_peta, lokasi_penting = muat_data_peta_dan_lokasi(lokasi_peta, distance=2000, network_type="drive", path_ke_geojson=path_geojson)

    if graf_peta is None:
        print("Graf tidak berhasil dimuat, selesai.")
    else:
        # 2. Analisis cut vertices & bridges
        cut_vertices, bridges = analisis_titik_rawan(graf_peta)

        # 3. Visualisasi - DIPISAH (sesuai pilihan Anda)
        visualisasi_cut_vertex(graf_peta, cut_vertices, title_suffix="(Highlight di atas peta)")
        visualisasi_cut_edges(graf_peta, bridges, title_suffix="(Highlight di atas peta)")

        # 4. (Opsional) contoh simulasi penghapusan: ambil satu cut vertex / bridge jika tersedia
        if cut_vertices:
            contoh_node = cut_vertices[0]
            print(f"\nContoh simulasi: menghapus cut vertex {contoh_node}")
            simulasi_putus_jalur(graf_peta, contoh_node)

        if bridges:
            contoh_edge = bridges[0]
            print(f"\nContoh simulasi: menghapus cut edge {contoh_edge}")
            simulasi_putus_jalur(graf_peta, contoh_edge)
