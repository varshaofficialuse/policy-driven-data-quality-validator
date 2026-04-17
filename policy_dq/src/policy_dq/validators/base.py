from abc import ABC, abstractmethod

import pandas as pd

from policy_dq.models import Rule, ValidationIssue


class BaseValidator(ABC):
    """Abstract base class for all rule validators."""

    def __init__(self, rule: Rule) -> None:
        self.rule = rule

    @abstractmethod
    def validate(self, series: pd.Series) -> list[ValidationIssue]:
        """Validate a column Series against the rule.

        Returns a list of ValidationIssue for every violation found.
        """
        ...
