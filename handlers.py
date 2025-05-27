# standard library
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any
import hashlib
import io
import json

# 3rd party libraries
import genson
import xmltodict
from decouple import config

# user modules
from tools import client


class FileHandlerBase(ABC):
    """
    Base class of a file handler.
    """

    def __init__(self, contents: str) -> None:
        self.contents = contents
        self._fields = set()
        self.client = client

        builder = genson.SchemaBuilder()
        builder.add_object(self.reference_object)
        schema = builder.to_schema()
        self.schema = self._sort_schema(schema)

    @property
    @abstractmethod
    def content_type(self) -> str:
        """Content type of a file. """
        raise NotImplementedError

    @property
    @abstractmethod
    def reference_object(self) -> Any:
        """The reference object that the built schema must satisfy. """
        raise NotImplementedError

    @cached_property
    def fields(self) -> list[str]:
        """Sorted unique fields of the schema. """
        self._fields = sorted(self._fields)
        return self._fields

    @cached_property
    def schema_bytes(self) -> bytes:
        """Serialized schema encoded to bytes. """
        return json.dumps(self.schema, indent=4).encode()

    @cached_property
    def schema_digest(self) -> int:
        """SHA256 digest value for the serialized schema. """
        return hashlib.sha256(self.schema_bytes).hexdigest()

    def add_schema(self) -> None:
        """Upload schema to the S3 bucket. """
        self.client.put_object(
            Bucket     =config("S3_BUCKET_NAME"),
            Key        =f"{self.schema_digest}.json",
            Body       =io.BytesIO(self.schema_bytes),
            ContentType="application/json"
        )
        return None

    def _sort_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Sort fields and values of the schema including nested items.
        Collect unique fields of the schema ignoring original order.
        """
        sort_funcs = {
            dict: self._sort_schema,  # sort nested dicts recursively
            list: sorted,             # sort string values of an array
            str: lambda value: value  # identity function skips strings
        }
        sorted_schema = {}
        for field, value in sorted(schema.items()):
            value_type = type(value)
            if field == "properties" and value_type is dict:
                self._fields.update(value)
            sorted_schema[field] = sort_funcs[value_type](value)
        return sorted_schema


class JSONHandler(FileHandlerBase):
    """
    JSON file handler.
    """

    content_type = "application/json"

    @property
    def reference_object(self) -> dict[str, Any]:
        """The reference object that the built schema must satisfy. """
        return json.loads(self.contents)


class XMLHandler(FileHandlerBase):
    """
    XML file handler.
    """

    content_type = "text/xml"

    @property
    def reference_object(self) -> dict[str, Any]:
        """The reference object that the built schema must satisfy. """
        return xmltodict.parse(self.contents)
