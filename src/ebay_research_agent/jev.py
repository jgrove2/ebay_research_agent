from typesafe_sdk import AsyncTypeSafeClient, Noul


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
    correct_product_threshold: float,
    worth_price_threshold: float,
    water_damage_threshold: float,
) -> bool:
    correct_product = result["nouls"]["correct_product"]["noul"]
    worth_price = result["nouls"]["worth_price"]["noul"]
    water_damage = result["nouls"]["water_damage"]["noul"]
    return (
        correct_product >= correct_product_threshold
        and worth_price >= worth_price_threshold
        and water_damage < water_damage_threshold
    )


def build_accept_questions() -> dict:
    return {
        "correct_product": Noul(
            instructions=(
                "Is this listing a console unit matching the product named in the "
                "state — not a game, accessory, controller, or a different console?"
            )
        ),
        "worth_price": Noul(
            instructions=(
                "Using the sold-value summary in the state, is the listing's total "
                "price (item + shipping) roughly half or less of the typical sold "
                "value, meaning there is room to profit after repairing or parting "
                "it out?"
            )
        ),
        "water_damage": Noul(
            instructions=(
                "Does the listing indicate water damage (liquid exposure, "
                "corrosion, waterlogged, or water damage)?"
            )
        ),
    }
