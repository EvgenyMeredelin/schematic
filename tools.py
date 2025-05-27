# standard library
from functools import reduce
from typing import Any
import json
import operator

# 3rd party libraries
from decouple import config
from spellchecker import SpellChecker
import boto3

import nltk
nltk.download("wordnet")
from nltk.corpus import wordnet


tenant_id = config("S3_TENANT_ID")
key_id    = config("S3_KEY_ID")

session = boto3.session.Session(
    aws_access_key_id    =f"{tenant_id}:{key_id}",
    aws_secret_access_key=config("S3_KEY_SECRET"),
    region_name          =config("S3_REGION_NAME")
)
client = session.client(
    service_name="s3",
    endpoint_url=config("S3_ENDPOINT_URL")
)


def retrieve_schema(digest: str) -> dict[str, Any]:
    """
    Retrieve schema from S3 bucket by the given digest.
    """
    schema = client.get_object(
        Bucket=config("S3_BUCKET_NAME"),
        Key   =f"{digest}.json"
    )
    return json.loads(schema["Body"].read())


def correct_spelling(words: list[str]) -> set[str]:
    """
    Return the most probable correct spellings for
    the given words.
    """
    spell = SpellChecker()
    misspelled = spell.unknown(words)
    return {
        correction for word in misspelled
        if (correction := spell.correction(word))
    }


def find_synonyms(words: list[str]) -> set[str]:
    """Find synonyms for the given words. """
    sets = [
        set(
            lemma.name()
            for syn in wordnet.synsets(word)
            for lemma in syn.lemmas()
        )
        for word in words
    ]
    # add original words if no synonyms found
    return set(words) | reduce(operator.or_, sets)


def is_substring(foo: str, bar: str) -> bool:
    """
    Test if a string is a substring of another,
    or vice versa.
    """
    foo, bar = map(str.lower, (foo, bar))
    return (foo in bar) or (bar in foo)
