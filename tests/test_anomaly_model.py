import random

from achchaosmonkey.validator.anomaly import AnomalyModel


def make_matrix(n: int, seed: int, anomalous: bool = False) -> list[list[float]]:
    rng = random.Random(seed)
    matrix = []
    for _ in range(n):
        base = [rng.gauss(0, 1) for _ in range(9)]
        if anomalous:
            base = [v * 8 for v in base]
        matrix.append(base)
    return matrix


def test_fit_and_score_without_error():
    model = AnomalyModel(contamination=0.1)
    matrix = make_matrix(200, seed=1)
    model.fit(matrix)
    assert model.fitted
    scores = model.score(matrix)
    assert len(scores) == len(matrix)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_unfitted_model_returns_zero_scores():
    model = AnomalyModel()
    scores = model.score(make_matrix(5, seed=2))
    assert scores == [0.0] * 5


def test_deterministic_scores_for_same_input():
    matrix = make_matrix(100, seed=3)
    model_a = AnomalyModel(contamination=0.1, random_state=42)
    model_a.fit(matrix)
    model_b = AnomalyModel(contamination=0.1, random_state=42)
    model_b.fit(matrix)
    assert model_a.score(matrix) == model_b.score(matrix)


def test_anomalous_points_score_higher_on_average():
    normal = make_matrix(300, seed=4, anomalous=False)
    model = AnomalyModel(contamination=0.1)
    model.fit(normal)

    normal_scores = model.score(make_matrix(50, seed=5, anomalous=False))
    anomalous_scores = model.score(make_matrix(50, seed=6, anomalous=True))

    assert sum(anomalous_scores) / len(anomalous_scores) > sum(normal_scores) / len(normal_scores)


def test_save_and_load_round_trip(tmp_path):
    matrix = make_matrix(150, seed=7)
    model = AnomalyModel(contamination=0.1)
    model.fit(matrix)
    path = model.save(tmp_path / "model.joblib")

    loaded = AnomalyModel.load(path)
    assert loaded.fitted
    assert loaded.score(matrix) == model.score(matrix)
