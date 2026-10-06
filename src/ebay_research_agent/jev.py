from typesafe_sdk import AsyncTypeSafeClient, Noul, Score


class JevClient:
    def __init__(self, api_key: str, model: str = "jev-latest") -> None:
        self._api_key = api_key
        self._model = model
        self._client: AsyncTypeSafeClient | None = None

    def _ensure_client(self) -> AsyncTypeSafeClient:
        if self._client is None:
            self._client = AsyncTypeSafeClient(api_key=self._api_key, model=self._model)
        return self._client

    async def evaluate(self, state: dict, questions: dict) -> dict:
        response = await self._ensure_client().system_one(
            state=state, questions=questions
        )
        return {
            "choices": {
                key: answer.model_dump() for key, answer in response.choices.items()
            },
            "nouls": {
                key: answer.model_dump() for key, answer in response.nouls.items()
            },
            "scores": {
                key: answer.model_dump() for key, answer in response.scores.items()
            },
        }

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


def should_accept(
    result: dict,
    fault_threshold: float,
    legit_threshold: float,
    profit_threshold: float,
) -> bool:
    fault_clarity = result["nouls"]["fault_clarity"]["noul"]
    legitimate = result["nouls"]["legitimate"]["noul"]
    profit_potential = result["scores"]["profit_potential"]["score"]
    return (
        fault_clarity >= fault_threshold
        and legitimate >= legit_threshold
        and profit_potential <= profit_threshold
    )


def build_accept_questions() -> dict:
    return {
        "fault_clarity": Noul(
            instructions="Does the listing clearly identify the primary fault or condition?"
        ),
        "legitimate": Noul(
            instructions="Is this a legitimate 'for parts / not working' listing "
            "(not mislabeled, not a scam)?"
        ),
        "profit_potential": Score(
            instructions=(
                "Relative to the sold-value comps provided in the state, how does the "
                "listing's total price compare to the expected resale or parts value?"
            ),
            criteria=[
                "well under expected value",
                "near expected value",
                "above expected value",
            ],
        ),
    }
