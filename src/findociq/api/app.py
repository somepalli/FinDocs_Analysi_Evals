"""FastAPI application with routes kept intentionally thin."""

import argparse
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request

from findociq.api.schema import HealthResponse, QueryRequest, QueryResponse
from findociq.service import ApiConfig, FinDocIQService, build_service


def create_app(
    service: FinDocIQService | None = None,
    *,
    config_path: Path = Path("configs/api/default.yaml"),
) -> FastAPI:
    app = FastAPI(title="FinDocIQ", version="0.1.0")
    app.state.query_service = service
    app.state.config_path = config_path

    def get_service(request: Request) -> FinDocIQService:
        current = request.app.state.query_service
        if current is None:
            current = build_service(ApiConfig.from_yaml(request.app.state.config_path))
            request.app.state.query_service = current
        return current

    @app.get("/healthz", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/v1/query", response_model=QueryResponse)
    def query(
        payload: QueryRequest,
        query_service: Annotated[FinDocIQService, Depends(get_service)],
    ) -> QueryResponse:
        mode = payload.mode or query_service.default_mode
        try:
            result = query_service.query(
                payload.question,
                mode=mode,
                question_id=payload.question_id,
            )
        except (RuntimeError, OSError) as error:
            raise HTTPException(
                status_code=503, detail="local inference pipeline unavailable"
            ) from error
        return QueryResponse(
            mode=mode,
            answer=result.answer.answer,
            citations=result.answer.citations,
        )

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--config", type=Path, default=Path("configs/api/default.yaml"))
    args = parser.parse_args()
    try:
        import uvicorn
    except ImportError as error:
        raise RuntimeError("API serving requires `uv sync --extra api`") from error
    uvicorn.run(create_app(config_path=args.config), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
