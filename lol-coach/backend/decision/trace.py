from dataclasses import dataclass


@dataclass
class TraceEntry:
    stage: str
    code: str
    detail: str | None = None


def build_trace(state, opportunities, permission, evaluations) -> list[TraceEntry]:
    trace: list[TraceEntry] = []

    for opportunity in opportunities:
        trace.append(
            TraceEntry(
                stage="OPPORTUNITY",
                code=opportunity.value,
            )
        )

    trace.append(
        TraceEntry(
            stage="PERMISSION",
            code=permission.name,
        )
    )

    return trace
