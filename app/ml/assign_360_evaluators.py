import numpy as np
import networkx as nx
from sklearn.cluster import SpectralClustering

def assign_360_evaluators_spectral(employees, num_clusters=3):
    """
    Uses Spectral Clustering to assign evaluators to employees.

    :param employees: List of employee dictionaries.
    :param num_clusters: Number of clusters to form.

    :return: Dictionary { evaluator_id: [peer_1_id, peer_2_id, ...] }
    """
    employees = [employee.to_dict() for employee in employees]
    G = nx.Graph()

    # Step 1: Add employees as nodes
    for employee in employees:
        # print(employee.to_dict()["id"])
        G.add_node(str(employee["id"]))

    # Step 2: Add edges based on organizational relationships
    for employee in employees:
        emp_id = str(employee["id"])
        
        if employee.get("direct_supervisor_id"):
            G.add_edge(emp_id, str(employee["direct_supervisor_id"]), weight=2.0)  # Stronger link
        
        if employee.get("functional_supervisor_id"):
            G.add_edge(emp_id, str(employee["functional_supervisor_id"]), weight=1.5)

    # Step 3: Convert graph to adjacency matrix
    adjacency_matrix = nx.to_numpy_array(G)

    # Step 4: Apply Spectral Clustering
    clustering = SpectralClustering(
        n_clusters=min(num_clusters, len(employees)),
        affinity="precomputed",
        random_state=42
    ).fit(adjacency_matrix)

    labels = clustering.labels_

    # Step 5: Assign evaluators based on clusters
    clustered_employees = {}
    for i, employee in enumerate(employees):
        cluster_id = labels[i]
        clustered_employees.setdefault(cluster_id, []).append(str(employee["id"]))

    evaluator_assignments = {}
    for cluster in clustered_employees.values():
        if len(cluster) > 1:
            for evaluator in cluster:
                peers = [peer for peer in cluster if peer != evaluator]
                evaluator_assignments[evaluator] = peers

    return evaluator_assignments
