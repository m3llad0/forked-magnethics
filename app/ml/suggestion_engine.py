import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist
from flask_sqlalchemy import SQLAlchemy
from node2vec import Node2Vec
from sklearn.cluster import AgglomerativeClustering
from sklearn.neighbors import NearestNeighbors

from app.models import Employee


class SuggestionEngine:
    """
    Per-tenant 360° suggestion engine with relationship classification.

    Usage:
        engine = SuggestionEngine(db, tenant_id, config)
        suggestions = engine.assign_suggestions()
        # suggestions is a dict { employee_number: [{employee_number, relation}, ...] }
    """

    def __init__(self,
                 db: SQLAlchemy,
                 tenant_id: str,
                 config: dict = None):
        self.db = db
        self.tenant_id = tenant_id

        # Default hyperparameters—override via `config`
        defaults = {
            "weight_ratio": (1.3, 1.0),        # direct_w, func_w
            "emb_dim": 64,                     # embedding dimension
            "threshold_percentile": 50,        # for dynamic clustering cutoff
            "knn_k": 5,                        # K in KNN index
            "top_k": 3,                        # how many targets per employee
        }
        self.config = {**defaults, **(config or {})}

        # Fetch employees once
        self.employees = self._get_employees()
        # internal IDs for graph
        self.ids = [e.id for e in self.employees]
        # public identifiers for lookup
        self.numbers = [e.employee_number for e in self.employees]

    def _get_employees(self):
        return (self.db.session.query(Employee)
                    .filter_by(client_id=self.tenant_id)
                    .all())

    def _build_weighted_graph(self):
        direct_w, func_w = self.config["weight_ratio"]
        G = nx.Graph()
        for e in self.employees:
            G.add_node(e.id)
            if e.direct_supervisor_id:
                G.add_edge(e.id, e.direct_supervisor_id, weight=direct_w)
            if e.functional_supervisor_id:
                G.add_edge(e.id, e.functional_supervisor_id, weight=func_w)
        return G

    def _compute_embeddings(self, G):
        n2v = Node2Vec(
            G,
            dimensions=self.config["emb_dim"],
            walk_length=30,
            num_walks=100,
            weight_key="weight",
            quiet=True,
        )
        model = n2v.fit(window=5, min_count=1)
        X = np.vstack([model.wv[str(n)] for n in self.ids])
        return X

    def _cluster_embeddings(self, X):
        pairwise = pdist(X, metric="euclidean")
        thresh = np.percentile(pairwise, self.config["threshold_percentile"])
        clust = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=thresh,
            metric="euclidean",
            linkage="average"
        )
        return clust.fit_predict(X)

    def _build_cluster_knn(self, X, labels):
        knn_index = {}
        k = self.config["knn_k"]
        for c in np.unique(labels):
            idxs = np.where(labels == c)[0]
            Xc = X[idxs]
            knn = NearestNeighbors(
                n_neighbors=min(len(idxs), k + 1),
                metric="euclidean"
            ).fit(Xc)
            knn_index[c] = (knn, idxs)
        return knn_index

    def _suggest_for_one(self, e, X, labels, knn_index):
        suggestions = []
        MAX = self.config["top_k"]

        # 1) Self-evaluation
        suggestions.append((e.employee_number, "Autoevaluación"))

        # 2) Direct supervisor
        if e.direct_supervisor_id:
            sup = next((x for x in self.employees if x.id == e.direct_supervisor_id), None)
            if sup:
                suggestions.append((sup.employee_number, "Jefe directo"))

        # 3) Subordinates (Colaboradores)
        subordinates = [emp for emp in self.employees if emp.direct_supervisor_id == e.id]
        for sub in subordinates:
            if len(suggestions) >= MAX:
                break
            suggestions.append((sub.employee_number, "Colaborador"))

        # 4) Homologous peers from same cluster
        i = self.ids.index(e.id)
        c = labels[i]
        knn, idxs = knn_index[c]
        dists, nbrs = knn.kneighbors([X[i]], n_neighbors=min(len(idxs), MAX + 1))

        for nb in nbrs[0]:
            peer = self.employees[idxs[nb]]
            if peer.id == e.id:
                continue  # skip self
            peer_num = peer.employee_number
            already_suggested = [x[0] for x in suggestions]
            if peer_num not in already_suggested and len(suggestions) < MAX:
                suggestions.append((peer_num, "Homólogo"))

        return suggestions

    def assign_suggestions(self) -> dict:
        """
        Runs the pipeline and returns a map:
            { employee_number: [ {employee_number, relation}, ... ] }
        """
        G = self._build_weighted_graph()
        X = self._compute_embeddings(G)
        labels = self._cluster_embeddings(X)
        knn_index = self._build_cluster_knn(X, labels)

        out = {}
        for e in self.employees:
            suggestions = self._suggest_for_one(e, X, labels, knn_index)
            out[e.employee_number] = [
                {"employee_number": emp_num, "relation": relation}
                for emp_num, relation in suggestions
            ]
        return out
