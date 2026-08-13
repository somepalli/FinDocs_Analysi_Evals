from pathlib import Path

from fastapi.testclient import TestClient

from findociq.api.app import create_app
from findociq.ingest.schema import BoundingBox
from findociq.reason.schema import ReasonedAnswer, ReasoningRun, SourceCitation
from findociq.service import ApiConfig

ROOT = Path(__file__).parents[1]


class FakeQueryService:
    default_mode = "two_pass"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, str, str | None]] = []

    def query(self, question: str, *, mode: str, question_id: str | None = None) -> ReasoningRun:
        self.calls.append((question, mode, question_id))
        if self.fail:
            raise RuntimeError("secret backend detail")
        return ReasoningRun(
            mode=mode,
            question=question,
            answer=ReasonedAnswer(
                answer="Revenue was Rs. 10 crore.",
                citations=(
                    SourceCitation(
                        document_id="doc-1",
                        page_number=2,
                        bbox=BoundingBox(x0=1, y0=2, x1=3, y1=4),
                    ),
                ),
            ),
        )


def test_api_config_resolves_reviewed_pipeline_paths() -> None:
    config = ApiConfig.from_yaml(ROOT / "configs/api/default.yaml")
    assert config.default_mode == "two_pass"
    assert config.generation_config.name == "gemma_vllm.yaml"
    assert config.observability_config.name == "langfuse.yaml"
    paths = (path for path in config.model_dump().values() if isinstance(path, Path))
    assert all(path.is_absolute() for path in paths)


def test_fastapi_query_is_thin_and_returns_mandatory_provenance() -> None:
    service = FakeQueryService()
    client = TestClient(create_app(service=service))  # type: ignore[arg-type]
    assert client.get("/healthz").json() == {"status": "ok", "service": "findociq"}
    response = client.post(
        "/v1/query",
        json={"question": "What was revenue?", "question_id": "q1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "two_pass"
    assert payload["citations"][0] == {
        "document_id": "doc-1",
        "page_number": 2,
        "bbox": {"x0": 1.0, "y0": 2.0, "x1": 3.0, "y1": 4.0},
    }
    assert service.calls == [("What was revenue?", "two_pass", "q1")]


def test_fastapi_does_not_leak_backend_error_details() -> None:
    client = TestClient(create_app(service=FakeQueryService(fail=True)))  # type: ignore[arg-type]
    response = client.post("/v1/query", json={"question": "What was revenue?"})
    assert response.status_code == 503
    assert response.json() == {"detail": "local inference pipeline unavailable"}
    assert "secret backend detail" not in response.text
