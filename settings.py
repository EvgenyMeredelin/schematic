# standard library
from enum import StrEnum

# https://rapidfuzz.github.io/Levenshtein/levenshtein.html#Levenshtein.ratio
LEVENSHTEIN_RATIO_SCORE_CUTOFF: float = 0.8


class SearchLogic(StrEnum):
    """
    Search logic corresponding to the Python built-in functions.
    """

    ALL = "all"
    ANY = "any"


class StatusComment(StrEnum):
    """
    Schema status comment.
    """

    JUST_ADDED  = "Just added by you."
    SEEN_BEFORE = "Seen before."
