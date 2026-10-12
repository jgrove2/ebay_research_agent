from typesafe_sdk import AsyncTypeSafeClient


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


def number_of_consoles(result: dict) -> int:
    raw = result.get("choices", {}).get("number_of_consoles", {}).get("choice")
    try:
        count = 10 if raw == "10+" else int(raw)
    except (TypeError, ValueError):
        return 1
    return max(count, 1)


def has_profit(
    per_console_cost: float | None,
    sold_average: float | None,
    profit_margin: float,
) -> bool:
    return (
        per_console_cost is not None
        and sold_average is not None
        and sold_average > 0
        and (sold_average - per_console_cost) / sold_average >= profit_margin
    )


def should_accept(
    result: dict,
    per_console_cost: float | None,
    sold_average: float | None,
    correct_product_threshold: float,
    water_damage_threshold: float,
    profit_margin: float,
) -> bool:
    correct_product = result["nouls"]["correct_product"]["noul"]
    water_damage = result["nouls"]["water_damage"]["noul"]
    return (
        correct_product >= correct_product_threshold
        and water_damage < water_damage_threshold
        and has_profit(per_console_cost, sold_average, profit_margin)
    )
