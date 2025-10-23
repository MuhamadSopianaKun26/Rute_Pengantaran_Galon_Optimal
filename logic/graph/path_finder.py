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
    """
    print("Memuat graf jaringan jalan dari OpenStreetMap...")
    try:
        # 1. Muat graf peta utama
        G = ox.graph_from_point(point, dist=distance, network_type=network_type)
        print("[OK] Graf peta berhasil dimuat.")
        
        # 2. Muat data lokasi penting dari file GeoJSON
        gdf_lokasi = gpd.read_file(path_ke_geojson)
        print("[OK] Data lokasi penting (GeoJSON) berhasil dimuat.")

        # Untuk melihat nama kolom
        print("Nama kolom yang tersedia di GeoJSON:", gdf_lokasi.columns)
        
        return G, gdf_lokasi
        
    except Exception as e:
        print(f"Gagal memuat data: {e}")
        return None, None

# =============================================================================
# FUNGSI INTI UNTUK DIJALANKAN DARI GUI (VERSI BARU)
# =============================================================================

def cari_rute_by_nama(G, gdf_lokasi, nama_awal, nama_akhir, show_preview: bool = False):
    """
    Fungsi utama yang mencari rute berdasarkan NAMA lokasi, bukan koordinat.

    Args:
        G (nx.Graph): Objek graf peta dari OSMnx.
        gdf_lokasi (gpd.GeoDataFrame): Tabel data lokasi dari GeoJSON.
        nama_awal (str): Nama lokasi awal (misal, "Depot Pusat").
        nama_akhir (str): Nama lokasi tujuan (misal, "Mitra_Sarijadi").
        show_preview (bool): Menampilkan preview rute jika True.

    Returns:
        tuple: Berisi (daftar_sisi_rute, panjang_rute) jika berhasil,
               atau (None, None) jika gagal.
    """
    try:
        # 1. Cari baris data untuk nama awal dan akhir di tabel GeoDataFrame
        lokasi_awal = gdf_lokasi[gdf_lokasi['intersection_name'] == nama_awal].iloc[0]
        lokasi_akhir = gdf_lokasi[gdf_lokasi['intersection_name'] == nama_akhir].iloc[0]
        
        # 2. Ambil koordinat dari geometri-nya
        coord_awal = (lokasi_awal.geometry.y, lokasi_awal.geometry.x)
        coord_akhir = (lokasi_akhir.geometry.y, lokasi_akhir.geometry.x)

        # 3. Terjemahkan koordinat ke ID simpul terdekat (sama seperti sebelumnya)
        node_awal = ox.distance.nearest_nodes(G, coord_awal[1], coord_awal[0])
        node_akhir = ox.distance.nearest_nodes(G, coord_akhir[1], coord_akhir[0])
        
        # 4. Jalankan Algoritma Dijkstra
        print(f"Mencari rute dari '{nama_awal}' (simpul {node_awal}) ke '{nama_akhir}' (simpul {node_akhir})...")
        shortest_path_nodes = nx.dijkstra_path(G, node_awal, node_akhir, weight='length')
        path_length = nx.dijkstra_path_length(G, node_awal, node_akhir, weight='length')
        path_length_km = path_length / 1000
        
        print(f"[OK] Rute ditemukan dengan panjang {path_length_km:.2f} km.")
        
        # 5. Siapkan data untuk GUI
        shortest_route_edges = list(zip(shortest_path_nodes, shortest_path_nodes[1:]))
        
        # (Opsional) Tampilkan preview sederhana lagi jika diperlukan
        # ox.plot_graph_route(G, shortest_path_nodes)

        if show_preview:
            print("Menampilkan jendela preview rute...")
            pos = {node: (data['x'], data['y']) for node, data in G.nodes(data=True)}
            
            # --- Visualisasi Lanjutan dengan Label dan Panah ---
            print("Menampilkan jendela preview rute di atas peta...")
            fig, ax = ox.plot_graph_route(
                G, 
                shortest_path_nodes, 
                route_color='red', 
                route_linewidth=4, 
                node_size=0, 
                bgcolor='#FFFFFF',
                show=False,
                close=False
            )
     
                
            # --- LANGKAH 1: Menambahkan Label Nama ---
            # Ambil simpul awal dan akhir
            start_node = shortest_path_nodes[0]
            end_node = shortest_path_nodes[-1]
            
            # Ambil koordinat x, y dari simpul tersebut
            start_coord_x = G.nodes[start_node]['x']
            start_coord_y = G.nodes[start_node]['y']
            end_coord_x = G.nodes[end_node]['x']
            end_coord_y = G.nodes[end_node]['y']
            
            # Tulis teks di atas peta. bbox memberi latar belakang agar mudah dibaca.
            ax.text(start_coord_x, start_coord_y, f"  START\n  {nama_awal}", fontsize=9, color='white', 
                    bbox=dict(facecolor='green', alpha=0.8, boxstyle="round,pad=0.3"))
            ax.text(end_coord_x, end_coord_y, f"  FINISH\n  {nama_akhir}", fontsize=9, color='white',
                    bbox=dict(facecolor='darkred', alpha=0.8, boxstyle="round,pad=0.3"))

            # --- LANGKAH 2: Menambahkan Panah Arah Tujuan ---
            # Ambil dua simpul terakhir di rute
            if len(shortest_path_nodes) >= 2:
                second_last_node = shortest_path_nodes[-2]
                
                # Ambil koordinatnya
                second_last_x = G.nodes[second_last_node]['x']
                second_last_y = G.nodes[second_last_node]['y']
                
                # Gambar panah dari simpul kedua terakhir ke simpul terakhir
                ax.annotate("",
                            xy=(end_coord_x, end_coord_y), # Titik tujuan panah
                            xytext=(second_last_x, second_last_y), # Titik awal panah
                            arrowprops=dict(arrowstyle="->", color="gold", linewidth=3, shrinkA=5, shrinkB=5)
                           )
        
            ax.set_title(f"Rute Tercepat: {nama_awal} -> {nama_akhir} ({path_length_km:.2f} km)")
            plt.show()
        
        return shortest_route_edges, path_length_km

    except IndexError:
        print(f"Error: Nama lokasi '{nama_awal}' atau '{nama_akhir}' tidak ditemukan di file GeoJSON.")
        return None, None
    except nx.NetworkXNoPath:
        print(f"Error: Tidak ada rute yang ditemukan antara '{nama_awal}' dan '{nama_akhir}'.")
        return None, None
    except Exception as e:
        print(f"Terjadi error: {e}")
        return None, None
    
# =============================================================================
# BAGIAN KONFIRMASI DJIKSTRA SAAT MENGEKSEKUSI PEMESANAN
# =============================================================================

def buat_visualisasi_timeline_dijkstra(G_peta, gdf_lokasi, path_nodes):
    """
    Membuat visualisasi rute Dijkstra dalam bentuk timeline zig-zag yang fleksibel.
    SEKARANG DENGAN LABEL BOBOT (JARAK) PADA SETIAP SISI.
    
    Args:
        G_peta (nx.Graph): Objek graf peta ASLI dari OSMnx, berisi data bobot.
        gdf_lokasi (gpd.GeoDataFrame): Tabel data lokasi dari GeoJSON.
        path_nodes (list): Daftar ID simpul dari rute Dijkstra.
    """
    print("Membuat visualisasi timeline rute yang fleksibel...")
    
    # --- Langkah 1: Siapkan Informasi Label Simpul ---
    nama_simpul_map = gdf_lokasi.set_index('osmid')['intersection_name'].to_dict()
    node_labels = {}
    for node_id in path_nodes:
        nama = nama_simpul_map.get(node_id, str(node_id))
        node_labels[node_id] = textwrap.fill(nama, width=20)

    # --- Langkah 2: Buat Layout Zig-Zag ---
    pos = {}
    # (Logika layout zig-zag tetap sama)
    nodes_per_row = 5
    x, y = 0, 0
    direction = 1
    for i, node_id in enumerate(path_nodes):
        pos[node_id] = (x, y)
        if (i + 1) % nodes_per_row == 0 and i < len(path_nodes) - 1:
            y -= 2
            direction *= -1
        else:
            x += direction

    # --- (BARU) Langkah 3: Siapkan Label Bobot Sisi ---
    edge_labels = {}
    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i+1]
        # Ambil data sisi dari graf peta ASLI (G_peta)
        panjang_meter = G_peta.get_edge_data(u, v)[0]['length']
        # Format ke km dengan 2 angka desimal
        panjang_km = f"{panjang_meter / 1000:.2f} km"
        edge_labels[(u, v)] = panjang_km

    # --- Langkah 4: Buat Graf Rute dan Gambar ---
    G_rute = nx.path_graph(path_nodes)
    
    num_rows = (len(path_nodes) - 1) // nodes_per_row + 1
    fig, ax = plt.subplots(figsize=(12, num_rows * 3))

    # Gambar simpul
    nx.draw_networkx_nodes(G_rute, pos, ax=ax, node_color='skyblue', node_size=1500)
    
    # Gambar sisi
    nx.draw_networkx_edges(G_rute, pos, ax=ax, width=2.0, edge_color='black', arrows=True, arrowsize=20, arrowstyle='-|>')
    
    # (BARU) Gambar label bobot pada sisi
    nx.draw_networkx_edge_labels(
        G_rute, pos,
        edge_labels=edge_labels,
        font_color='red',
        font_size=8,
        ax=ax
    )
    
    # Gambar label nama di bawah simpul
    for i, node_id in enumerate(path_nodes):
        x_coord, y_coord = pos[node_id]
        label_text = f"{i+1}\n{node_labels[node_id]}"
        ax.text(x_coord, y_coord - 0.5, label_text, ha='center', va='top', fontsize=8)

    ax.axis('off')
    ax.set_title("Konfirmasi Rute Pengantaran (Timeline Perjalanan)", fontsize=14, pad=15)
    plt.tight_layout()
    plt.show()

# =============================================================================
# FUNGSI 1: ANALISIS PROAKTIF (Mencari Semua Titik Rawan)
# =============================================================================
def analisis_titik_rawan(G):
    """
    Menganalisis keseluruhan graf untuk menemukan semua Cut Vertices dan Cut Edges.
    
    Args:
        G (nx.Graph): Objek graf peta dari OSMnx.

    Returns:
        tuple: Berisi (daftar_cut_vertices, daftar_cut_edges).
    """
    print("Mencari semua titik dan jalur krusial...")
    cut_vertices = list(nx.articulation_points(G))
    bridges = list(nx.bridges(G))
    
    print(f"✅ Ditemukan {len(cut_vertices)} titik krusial (cut vertex).")
    print(f"✅ Ditemukan {len(bridges)} jalur krusial (bridge/cut edge).")
    
    return cut_vertices, bridges


# =============================================================================
# FUNGSI 2: SIMULASI REAKTIF (Sesuai Permintaan Anda)
# =============================================================================
def simulasi_putus_jalur(G, elemen_diputus):
    """
    Mensimulasikan dampak dari penghapusan sebuah simpul (persimpangan) 
    atau sisi (jalan), lalu memvisualisasikan hasilnya.

    Args:
        G (nx.Graph): Objek graf peta ASLI.
        elemen_diputus (int atau tuple): ID simpul yang ingin dihapus (int) 
                                       atau tuple sisi yang ingin dihapus (u, v).
    """
    if not elemen_diputus:
        print("Tidak ada elemen yang dipilih untuk diputus.")
        return

    # PENTING: Selalu buat salinan graf agar graf asli tidak rusak!
    G_copy = G.copy()
    
    nama_elemen = str(elemen_diputus)
    
    # Cek apakah elemen adalah simpul atau sisi, lalu hapus
    if isinstance(elemen_diputus, (int, str)): # Jika input adalah ID simpul
        print(f"Mensimulasikan penutupan persimpangan: {nama_elemen}...")
        G_copy.remove_node(elemen_diputus)
        tipe = "Persimpangan"
    elif isinstance(elemen_diputus, tuple) and len(elemen_diputus) == 2: # Jika input adalah sisi
        print(f"Mensimulasikan penutupan jalan: {nama_elemen}...")
        # Pastikan sisi ada sebelum mencoba menghapus
        if G_copy.has_edge(*elemen_diputus):
            G_copy.remove_edge(*elemen_diputus)
            tipe = "Jalan"
        else:
            print(f"Error: Sisi {nama_elemen} tidak ditemukan di graf.")
            return
    else:
        print("Error: Input elemen tidak valid.")
        return

    # Analisis dampak setelah penghapusan
    if nx.is_connected(G_copy):
        status = "Jaringan TETAP TERHUBUNG."
    else:
        jumlah_komponen = nx.number_connected_components(G_copy)
        status = f"Jaringan TERPUTUS menjadi {jumlah_komponen} bagian!"

    print(f"Hasil: {status}")

    # Visualisasi dampak
    fig, ax = ox.plot_graph(G_copy, node_size=10, edge_linewidth=0.8, show=False, close=False)
    ax.set_title(f"Dampak Penutupan {tipe} {nama_elemen}\n{status}")
    plt.show()

# =============================================================================
# CONTOH PENGGUNAAN
# =============================================================================
if __name__ == "__main__":
    # Koordinat pusat area Ciwaruga, Bandung
    lokasi_peta = (-6.872, 107.578)
    
    # Path ke file GeoJSON Anda
    path_geojson = "intersections_area.geojson"
    
    # 1. Muat semua data (cukup sekali)
    graf_peta, lokasi_penting = muat_data_peta_dan_lokasi(lokasi_peta, path_ke_geojson=path_geojson)
    
    if graf_peta is not None and lokasi_penting is not None:
        # 2. Tentukan nama lokasi untuk simulasi
        nama_depot = "Depot Air Pusat" # Ganti sesuai nama di GeoJSON
        nama_tujuan = "Jalan Sariasih & Jalan Sarimanah & Jalan Sarkasih I" # Ganti sesuai nama di GeoJSON
        
        # 3. Jalankan fungsi utama untuk mendapatkan data rute
        hasil_sisi, hasil_panjang = cari_rute_by_nama(graf_peta, lokasi_penting, nama_depot, nama_tujuan, show_preview=True)
        
        # 4. Jika rute berhasil ditemukan, jalankan visualisasi timeline
        if hasil_sisi:
            print("\n--- DATA UNTUK DIBERIKAN KE GUI PyQt6 ---")
            print(f"Rute dari {nama_depot} ke {nama_tujuan}:")
            print(f"1. Daftar Sisi Rute (untuk diwarnai): {hasil_sisi}")
            print(f"2. Panjang Rute: {hasil_panjang:.2f} km")
            
            # --- (BARU) Rekonstruksi daftar simpul dari daftar sisi ---
            # Kita buat kembali daftar simpulnya agar bisa dipakai oleh fungsi timeline
            if hasil_sisi:
                reconstructed_path_nodes = [hasil_sisi[0][0]] + [edge[1] for edge in hasil_sisi]
                
                # Panggil fungsi visualisasi timeline dengan data yang sudah direkonstruksi
                buat_visualisasi_timeline_dijkstra(graf_peta, lokasi_penting, reconstructed_path_nodes)
