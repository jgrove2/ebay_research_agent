from pydantic import BaseModel, Field


class IssuesResult(BaseModel):
    issues: list[str] = Field(
        description="Common issues or failure points for the console"
    )
    blurb: str = Field(
        description="What to look for when browsing 'for parts' listings for this console"
    )


class JudgedListing(BaseModel):
    product: str = Field(
        description="Console model/version identified from the listing"
    )
    issue: str = Field(
        description="Primary fault label, e.g. 'no power', 'disc-drive failure', or 'unknown'"
    )
    totalPrice: str = Field(description="Total price including shipping, e.g. '$45.00'")
    url: str = Field(description="Listing URL")


class JudgementBatch(BaseModel):
    listings: list[JudgedListing] = Field(
        description="Cleaned assessment for each listing"
    )
