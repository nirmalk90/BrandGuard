from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]
Role = Literal["creator", "reviewer", "admin"]
Severity = Literal["critical", "high", "medium", "low"]
Evidence = Literal["SUPPORTED", "CONTRADICTED", "NOT_SUBSTANTIATED", "NEEDS_HUMAN_REVIEW"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Profile(Input):
    name: Title
    description: str = Field(default="", max_length=1000)
    industry: str = Field(default="", max_length=100)
    audience: str = Field(default="", max_length=300)
    personality: str = Field(default="", max_length=300)
    style: str = Field(default="", max_length=300)
    tone: str = Field(default="", max_length=300)
    primary_color: str = Field(default="#3DE0C2", pattern=r"^#[a-fA-F0-9]{6}$")
    secondary_color: str = Field(default="#5B8FF9", pattern=r"^#[a-fA-F0-9]{6}$")


class Source(Input):
    title: Title
    content: Content


class Rule(Input):
    title: Title
    category: Literal["Terminology", "Promotional claim", "Approved fact", "Tone", "Clarity"]
    kind: Literal["phrase", "required", "price_floor", "approved_fact"]
    description: Annotated[str, StringConstraints(min_length=1, max_length=1200)]
    severity: Severity
    pattern: str = Field(default="", max_length=160)
    replacement: str = Field(default="", max_length=300)
    source_id: str = Field(min_length=36, max_length=36)
    value: int | None = Field(default=None, gt=0, le=100000000)
    valid_from: date | None = None
    valid_until: date | None = None
    active: bool = True

    @model_validator(mode="after")
    def check_rule(self):
        if self.kind == "price_floor" and (self.value is None or not self.pattern):
            raise ValueError("Enter a monthly minimum and a scope term, such as plans.")
        if self.kind in {"phrase", "required"} and not self.pattern:
            raise ValueError("Enter the phrase this rule checks.")
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("End date must be on or after the start date.")
        return self


class ReviewInput(Input):
    content: str = Field(default="", max_length=20000)
    artwork_id: str | None = Field(default=None, min_length=36, max_length=36)
    use_ai: bool = False

    @model_validator(mode="after")
    def has_material(self):
        if not self.content and not self.artwork_id:
            raise ValueError("Add copy or attach artwork to review.")
        return self


class SubmissionInput(ReviewInput):
    title: Title
    campaign: str = Field(default="Unassigned", min_length=1, max_length=100)
    content_type: str = Field(min_length=1, max_length=64)
    platform: str = Field(min_length=1, max_length=64)


class Decision(Input):
    action: Literal["APPROVED", "REJECTED", "CHANGES_REQUESTED"]
    comment: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    generation: int = Field(ge=1)


class Submit(Input):
    generation: int = Field(ge=1)


class RevisionInput(ReviewInput):
    generation: int = Field(ge=1)


class Contest(Input):
    status: Literal["DISMISSED", "CONTESTED", "OPEN"]
    reason: Annotated[str, StringConstraints(min_length=1, max_length=1200)]
    generation: int = Field(ge=1)


class Finding(BaseModel):
    category: str
    severity: Severity
    original_text: str
    explanation: str
    suggested_correction: str
    evidence_status: Evidence
    requires_human_review: bool
    rule_id: str | None = None
    rule_title: str | None = None
    rule_version: int | None = None
    source_id: str | None = None
    source_title: str | None = None
    source_version: int | None = None
    source_excerpt: str | None = None
    origin: Literal["copy", "artwork"] = "copy"
    regions: list[list[float]] = Field(default_factory=list)
    policy_key: str | None = None
    conflict: bool = False
