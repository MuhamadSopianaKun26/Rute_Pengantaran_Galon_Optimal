"""
Graph Algorithms untuk AquaGalon Application
Implementasi algoritma graph theory untuk sistem pengiriman galon

Algorithms:
- Dijkstra's Algorithm (Shortest Path)
- Cut Vertex Detection
- Cut Edge Detection  
- Graph Coloring
"""

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from typing import Dict, List, Tuple, Set, Optional


class GalonDeliveryGraph:
    """
    Graph representation untuk sistem pengiriman galon
    Mengelola depot, mitra, dan alamat customer
    """
    
    def __init__(self):
        self.graph = nx.Graph()
        self.depot_location = "Depot Pusat"
        self.mitra_locations = {
            "Mitra Ciwaruga": ["Jln. Ciwaruga"],
            "Mitra Gerlong": ["Jln. Gerlong Hilir"],
            "Mitra Sariasih": ["Jln. Sariasih", "Jln. Sarijadi Raya"],
            "Mitra Sarimanah": ["Jln. Sarimanah", "Jln. Sarirasa"]
        }
        self.all_locations = [
            "Depot Pusat",
            "Jln. Ciwaruga", "Jln. Gerlong Hilir", "Jln. Sarijadi Raya",
            "Jln. Sarirasa", "Jln. Sariasih", "Jln. Sarimanah", "Jln. Kampus Polban"
        ]
        self.setup_graph()
    
    def setup_graph(self):
        """Setup initial graph dengan lokasi dan edges"""
        # Add all nodes
        for location in self.all_locations:
            self.graph.add_node(location)
        
        # Add edges dengan bobot jarak (simulasi)
        # Format: (node1, node2, weight)
        edges = [
            ("Depot Pusat", "Jln. Ciwaruga", 5.2),
            ("Depot Pusat", "Jln. Gerlong Hilir", 4.8),
            ("Depot Pusat", "Jln. Sarijadi Raya", 3.5),
            ("Depot Pusat", "Jln. Sarirasa", 6.1),
            ("Depot Pusat", "Jln. Sariasih", 4.2),
            ("Depot Pusat", "Jln. Sarimanah", 5.8),
            ("Depot Pusat", "Jln. Kampus Polban", 7.2),
            
            # Inter-location connections
            ("Jln. Ciwaruga", "Jln. Gerlong Hilir", 3.2),
            ("Jln. Gerlong Hilir", "Jln. Sarijadi Raya", 2.8),
            ("Jln. Sarijadi Raya", "Jln. Sariasih", 2.1),
            ("Jln. Sariasih", "Jln. Sarimanah", 3.4),
            ("Jln. Sarimanah", "Jln. Sarirasa", 2.9),
            ("Jln. Sarirasa", "Jln. Kampus Polban", 4.5),
            ("Jln. Kampus Polban", "Jln. Ciwaruga", 6.8),
        ]
        
        for edge in edges:
            self.graph.add_edge(edge[0], edge[1], weight=edge[2])
    
    def dijkstra_shortest_path(self, start: str, end: str) -> Tuple[List[str], float]:
        """
        Implementasi Dijkstra algorithm untuk shortest path
        
        Args:
            start: Node awal
            end: Node tujuan
            
        Returns:
            Tuple[path, total_distance]
        """
        try:
            path = nx.shortest_path(self.graph, start, end, weight='weight')
            distance = nx.shortest_path_length(self.graph, start, end, weight='weight')
            return path, distance
        except nx.NetworkXNoPath:
            return [], float('inf')
    
    def find_cut_vertices(self) -> Set[str]:
        """
        Temukan cut vertices (articulation points)
        Node yang jika dihapus akan memutus konektivitas graph
        
        Returns:
            Set of cut vertices
        """
        return set(nx.articulation_points(self.graph))
    
    def find_cut_edges(self) -> Set[Tuple[str, str]]:
        """
        Temukan cut edges (bridges)
        Edge yang jika dihapus akan memutus konektivitas graph
        
        Returns:
            Set of cut edges
        """
        return set(nx.bridges(self.graph))
    
    def graph_coloring(self) -> Dict[str, int]:
        """
        Implementasi graph coloring untuk optimasi rute
        Useful untuk menghindari konflik pengiriman
        
        Returns:
            Dictionary mapping node to color
        """
        return nx.greedy_color(self.graph, strategy='largest_first')
    
    def get_mitra_for_location(self, location: str) -> Optional[str]:
        """
        Dapatkan mitra yang menaungi lokasi tertentu
        
        Args:
            location: Nama lokasi
            
        Returns:
            Nama mitra atau None
        """
        for mitra, locations in self.mitra_locations.items():
            if location in locations:
                return mitra
        return None
    
    def get_delivery_route(self, customer_address: str) -> Dict:
        """
        Dapatkan informasi lengkap rute pengiriman
        
        Args:
            customer_address: Alamat customer
            
        Returns:
            Dictionary dengan informasi rute
        """
        # Cari shortest path dari depot ke customer
        path, distance = self.dijkstra_shortest_path(self.depot_location, customer_address)
        
        # Dapatkan mitra yang menaungi
        mitra = self.get_mitra_for_location(customer_address)
        
        # Analisis cut vertices dan edges
        cut_vertices = self.find_cut_vertices()
        cut_edges = self.find_cut_edges()
        
        # Graph coloring
        coloring = self.graph_coloring()
        
        return {
            'path': path,
            'distance': distance,
            'mitra': mitra,
            'cut_vertices_in_path': [node for node in path if node in cut_vertices],
            'cut_edges_in_path': [(u, v) for u, v in zip(path[:-1], path[1:]) 
                                 if (u, v) in cut_edges or (v, u) in cut_edges],
            'path_colors': [coloring.get(node, 0) for node in path],
            'total_nodes': len(path),
            'risk_level': self.calculate_risk_level(path, cut_vertices, cut_edges)
        }
    
    def calculate_risk_level(self, path: List[str], cut_vertices: Set[str], 
                           cut_edges: Set[Tuple[str, str]]) -> str:
        """
        Hitung tingkat risiko berdasarkan cut vertices dan edges dalam path
        
        Returns:
            Risk level: 'Low', 'Medium', 'High'
        """
        risk_score = 0
        
        # Tambah score untuk cut vertices
        for node in path:
            if node in cut_vertices:
                risk_score += 2
        
        # Tambah score untuk cut edges
        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])
            if edge in cut_edges or (edge[1], edge[0]) in cut_edges:
                risk_score += 3
        
        if risk_score == 0:
            return 'Low'
        elif risk_score <= 3:
            return 'Medium'
        else:
            return 'High'


class GraphVisualizer:
    """
    Visualizer untuk menampilkan graph dalam PyQt6 application
    """
    
    def __init__(self, graph_data: GalonDeliveryGraph):
        self.graph_data = graph_data
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        
    def create_route_visualization(self, route_info: Dict) -> FigureCanvas:
        """
        Buat visualisasi rute pengiriman
        
        Args:
            route_info: Output dari get_delivery_route()
            
        Returns:
            FigureCanvas untuk ditampilkan di PyQt6
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Setup layout graph
        pos = nx.spring_layout(self.graph_data.graph, seed=42, k=3, iterations=50)
        
        # Draw all edges (light gray)
        nx.draw_networkx_edges(self.graph_data.graph, pos, ax=ax, 
                              edge_color='lightgray', width=1, alpha=0.5)
        
        # Highlight shortest path
        path = route_info['path']
        if len(path) > 1:
            path_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
            nx.draw_networkx_edges(self.graph_data.graph, pos, edgelist=path_edges,
                                  ax=ax, edge_color='#4A90A4', width=4, alpha=0.8)
        
        # Draw nodes with different colors
        node_colors = []
        for node in self.graph_data.graph.nodes():
            if node == self.graph_data.depot_location:
                node_colors.append('#E74C3C')  # Red for depot
            elif node in path:
                node_colors.append('#27AE60')  # Green for path nodes
            else:
                node_colors.append('#BDC3C7')  # Gray for other nodes
        
        nx.draw_networkx_nodes(self.graph_data.graph, pos, ax=ax,
                              node_color=node_colors, node_size=800, alpha=0.9)
        
        # Draw labels
        nx.draw_networkx_labels(self.graph_data.graph, pos, ax=ax,
                               font_size=8, font_weight='bold')
        
        # Highlight cut vertices
        cut_vertices = route_info['cut_vertices_in_path']
        if cut_vertices:
            cut_pos = {node: pos[node] for node in cut_vertices}
            nx.draw_networkx_nodes(self.graph_data.graph, cut_pos, ax=ax,
                                  node_color='orange', node_size=1000, alpha=0.7)
        
        # Add title and info
        ax.set_title(f"Rute Pengiriman ke {path[-1] if path else 'Unknown'}\n"
                    f"Jarak: {route_info['distance']:.1f} km | "
                    f"Risiko: {route_info['risk_level']}", 
                    fontsize=14, fontweight='bold')
        
        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#E74C3C', 
                      markersize=10, label='Depot'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#27AE60', 
                      markersize=10, label='Rute Terpilih'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', 
                      markersize=10, label='Cut Vertex'),
            plt.Line2D([0], [0], color='#4A90A4', linewidth=4, label='Shortest Path')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        ax.set_aspect('equal')
        ax.axis('off')
        self.figure.tight_layout()
        
        return self.canvas


# Factory function untuk mudah digunakan
def create_graph_system() -> Tuple[GalonDeliveryGraph, GraphVisualizer]:
    """
    Factory function untuk membuat graph system
    
    Returns:
        Tuple[GalonDeliveryGraph, GraphVisualizer]
    """
    graph_data = GalonDeliveryGraph()
    visualizer = GraphVisualizer(graph_data)
    return graph_data, visualizer


# Test functions
def test_algorithms():
    """Test semua algoritma graph"""
    graph = GalonDeliveryGraph()
    
    print("=== AquaGalon Graph Analysis ===")
    print(f"Total nodes: {graph.graph.number_of_nodes()}")
    print(f"Total edges: {graph.graph.number_of_edges()}")
    
    # Test shortest path
    start = "Depot Pusat"
    end = "Jln. Kampus Polban"
    path, distance = graph.dijkstra_shortest_path(start, end)
    print(f"\nShortest path from {start} to {end}:")
    print(f"Path: {' -> '.join(path)}")
    print(f"Distance: {distance:.1f} km")
    
    # Test cut vertices
    cut_vertices = graph.find_cut_vertices()
    print(f"\nCut vertices: {cut_vertices}")
    
    # Test cut edges
    cut_edges = graph.find_cut_edges()
    print(f"Cut edges: {cut_edges}")
    
    # Test graph coloring
    coloring = graph.graph_coloring()
    print(f"\nGraph coloring: {coloring}")
    
    # Test delivery route
    route_info = graph.get_delivery_route("Jln. Kampus Polban")
    print(f"\nDelivery route info:")
    for key, value in route_info.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_algorithms()
