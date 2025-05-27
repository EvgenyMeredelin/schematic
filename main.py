# standard library
from contextlib import asynccontextmanager
from datetime import datetime
from itertools import product
from typing import Any, Annotated
import importlib
import inspect

# 3rd party libraries
from decouple import config
from fastapi import (
    Depends, FastAPI, HTTPException, Query, UploadFile, status
)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse
import Levenshtein
import uvicorn

# user modules
from database import create_all_tables, get_async_session
from models import Record
from settings import (
    LEVENSHTEIN_RATIO_SCORE_CUTOFF, SearchLogic, StatusComment
)
from tools import (
    correct_spelling, find_synonyms, is_substring, retrieve_schema
)


# dynamically collect available file handlers
handlers_module = importlib.import_module("handlers")
handlers_menu = {
    obj.content_type: obj
    for name, obj in inspect.getmembers(handlers_module)
    if name.endswith("Handler")
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context function to perform startup and shutdown tasks. """
    await create_all_tables()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Schematic",
    description="Simple document schema parser and catalog.",
    version="0.1.0",
    contact={
        "name" : "Evgeny Meredelin",
        "email": "eimeredelin@sberbank.ru"
    }
)


@app.post("/file")
async def handle_uploaded_file(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    file   : UploadFile
) -> dict[str, Any]:
    """
    Endpoint responsible for the handling of uploaded file.

    Detect file content type, build the schema and extract fields
    with respective handler. Store collected data in the database
    and S3 object storage.

    Return collected data including schema and fields.
    """

    content_type = file.content_type
    handler_class = handlers_menu.get(content_type)
    if handler_class is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No handler for file with {content_type=}"
        )
    content = await file.read()
    handler = handler_class(content.decode())

    digests_match = (Record.digest == handler.schema_digest)
    find_date = select(Record.date_added).where(digests_match)
    result = await session.execute(find_date)
    date_added = result.scalars().first()

    if date_added is None:
        date_added = datetime.now()
        new_records = [  # create new db records
            Record(
                date_added  =date_added,
                content_type=content_type,
                digest      =handler.schema_digest,
                field       =field
            )
            for field in handler.fields
        ]
        session.add_all(new_records)
        await session.commit()
        handler.add_schema()
        comment = StatusComment.JUST_ADDED
    else:
        comment = StatusComment.SEEN_BEFORE

    return {
        "filename"    : file.filename,
        "content_type": content_type,
        "fields"      : handler.fields,
        "schema"      : handler.schema,
        "status"      : {"comment": comment, "date_added": date_added}
    }


@app.get("/search")
async def search_for_schemas(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    fields : Annotated[list[str],    Query()],
    logic  : Annotated[SearchLogic,  Query()] = SearchLogic.ANY
) -> dict[str, Any]:
    """
    Endpoint responsible for the schemas search by the given fields
    and the logic corresponding to the Python built-in functions.

    `all` assumes provided fields must be a subset of the candidate
    schema fields set.

    In mode `any`, fields checked for typos and corrected, enriched
    with synonyms and compared to the fields in the database using
    the normalized Levenshtein distance.

    Response contains detected similar fields, schemas and original
    search data.
    """

    if logic == SearchLogic.ALL:
        similar_fields = None  # not applicable
        group_fields_by_digest = (
            select(Record.digest, func.group_concat(Record.field))
            .group_by(Record.digest)
        )
        result = await session.execute(group_fields_by_digest)
        schemas = [
            retrieve_schema(digest)
            for digest, schema_fields in result
            if set(schema_fields.split(",")).issuperset(fields)
        ]

    elif logic == SearchLogic.ANY:
        result = await session.execute(select(Record.field))
        all_fields = result.scalars().unique()
        words = correct_spelling(fields) | find_synonyms(fields)
        similar_fields = {
            field for field, word in product(all_fields, words)
            if is_substring(field, word) or Levenshtein.ratio(
                field, word, processor=str.lower,
                # ratio turns to 0 (which is False) if it's less
                # than the cutoff threshold
                score_cutoff=LEVENSHTEIN_RATIO_SCORE_CUTOFF
            )
        }
        fields_match = Record.field.in_(similar_fields)
        find_digests = select(Record.digest).where(fields_match)
        result = await session.execute(find_digests)
        digests = result.scalars().unique()
        schemas = [retrieve_schema(digest) for digest in digests]

    return {
        "fields"        : fields,
        "similar_fields": similar_fields,
        "logic"         : logic,
        "schemas"       : schemas
    }


@app.get("/", status_code=status.HTTP_308_PERMANENT_REDIRECT)
async def redirect_from_root_to_docs():
    """Redirect from root to FastAPI Swagger docs. """
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config("HOST"),
        port=int(config("PORT")),
        reload=True
    )
