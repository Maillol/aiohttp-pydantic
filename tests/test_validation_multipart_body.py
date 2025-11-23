from __future__ import annotations

import aiohttp
from aiohttp import web
from pydantic import BaseModel

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.decorator import inject_params
import pytest

from aiohttp_pydantic.uploaded_file import UploadedFile, MultipartReadingError


class BookModel(BaseModel):
    title: str
    nb_page: int


class BookAndUploadFileView(PydanticView):
    async def post(self, book: BookModel, page_1: UploadedFile, page_2: UploadedFile):
        content_1 = (await page_1.read()).decode("utf-8")
        content_2 = (await page_2.read()).decode("utf-8")
        return web.json_response(
            {"book": book.model_dump(), "content_1": content_1, "content_2": content_2},
            status=201,
        )


@inject_params
async def post_book_and_upload_file(
    book: BookModel, page_1: UploadedFile, page_2: UploadedFile
):
    content_1 = (await page_1.read()).decode("utf-8")
    content_2 = (await page_2.read()).decode("utf-8")
    return web.json_response(
        {"book": book.model_dump(), "content_1": content_1, "content_2": content_2},
        status=201,
    )


class UploadFileView(PydanticView):
    async def post(self, document: UploadedFile):
        content = (await document.read()).decode("utf-8")
        return web.json_response({"content": content}, status=201)


@inject_params
async def post_file(document: UploadedFile):
    content = (await document.read()).decode("utf-8")
    return web.json_response({"content": content}, status=201)


class BuggedUploadFileView(PydanticView):

    async def post(self, page_1: UploadedFile, page_2: UploadedFile):
        try:
            (await page_2.read()).decode("utf-8")
            (await page_1.read()).decode("utf-8")
        except MultipartReadingError as error:
            return web.json_response(
                {"error": str(error)},
                status=500,
            )
        raise AssertionError("MultipartReadingError should be raised")


@inject_params
async def post_bugged_upload_file(self, page_1: UploadedFile, page_2: UploadedFile):
    try:
        (await page_2.read()).decode("utf-8")
        (await page_1.read()).decode("utf-8")
    except MultipartReadingError as error:
        return web.json_response(
            {"error": str(error)},
            status=500,
        )
    raise AssertionError("MultipartReadingError should be raised")


def build_app_with_pydantic_view_1():
    app = web.Application()
    app.router.add_view("/upload-file", UploadFileView)
    app.router.add_view("/book-and-files", BookAndUploadFileView)
    app.router.add_view("/bugged", BuggedUploadFileView)
    return app


def build_app_with_decorated_handler_1():
    app = web.Application()
    app.router.add_view("/upload-file", UploadFileView)
    app.router.add_post("/book-and-files", post_book_and_upload_file)
    app.router.add_post("/bugged", BuggedUploadFileView)
    return app


app_builders_1 = [build_app_with_pydantic_view_1, build_app_with_decorated_handler_1]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_post_json_and_upload_files(app_builder, aiohttp_client):
    client = await aiohttp_client(app_builder())
    with aiohttp.MultipartWriter("form-data") as multipart:
        multipart.append_json(
            {"title": "Les trois petits cochons", "nb_page": "2"},
            headers={
                "Content-Disposition": 'form-data; name="book"',
                "Content-Type": "application/json",
            },
        )
        multipart.append(
            "Chapitre 1: Maison en paille ...",
            headers={
                "Content-Disposition": 'form-data; name="page_1"; filename="chap1.txt"'
            },
        )
        multipart.append(
            "Chapitre 2: Maison en bois ...",
            headers={
                "Content-Disposition": 'form-data; name="page_2"; filename="chap1.txt"'
            },
        )

        resp = await client.post("/book-and-files", data=multipart)

    assert resp.status == 201
    assert await resp.json() == {
        "book": {"title": "Les trois petits cochons", "nb_page": 2},
        "content_1": "Chapitre 1: Maison en paille ...",
        "content_2": "Chapitre 2: Maison en bois ...",
    }


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_upload_file(app_builder, aiohttp_client):
    client = await aiohttp_client(app_builder())
    with aiohttp.MultipartWriter("form-data") as multipart:
        multipart.append(
            "foo bar",
            headers={
                "Content-Disposition": 'form-data; name="document"; filename="document.txt"'
            },
        )
        resp = await client.post("/upload-file", data=multipart)

    assert resp.status == 201
    assert await resp.json() == {"content": "foo bar"}


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_missing_file(app_builder, aiohttp_client):
    client = await aiohttp_client(app_builder())
    with aiohttp.MultipartWriter("form-data") as multipart:
        multipart.append_json(
            {"title": "Les trois petits cochons", "nb_page": "2"},
            headers={
                "Content-Disposition": 'form-data; name="book"',
                "Content-Type": "application/json",
            },
        )
        multipart.append(
            "Chapitre 2: Maison en bois ...",
            headers={
                "Content-Disposition": 'form-data; name="page_2"; filename="chap1.txt"'
            },
        )

        resp = await client.post("/book-and-files", data=multipart)

    assert resp.status == 400
    assert await resp.json() == [
        {
            "in": "body",
            "loc": ["__root__"],
            "msg": 'The expected part name is "page_1" but the provided part name is "page_2"',
            "type": "type_error.multipart",
        }
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_missing_object(app_builder, aiohttp_client):
    client = await aiohttp_client(app_builder())
    with aiohttp.MultipartWriter("form-data") as multipart:
        multipart.append(
            "Chapitre 1: Maison en paille ...",
            headers={
                "Content-Disposition": 'form-data; name="page_1"; filename="chap1.txt"'
            },
        )
        multipart.append(
            "Chapitre 2: Maison en bois ...",
            headers={
                "Content-Disposition": 'form-data; name="page_2"; filename="chap1.txt"'
            },
        )
        resp = await client.post("/book-and-files", data=multipart)

    assert resp.status == 400
    assert await resp.json() == [
        {
            "in": "body",
            "loc": ["__root__"],
            "msg": 'The expected part name is "book" but the provided part name is "page_1"',
            "type": "type_error.multipart",
        }
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_missing_last_part(app_builder, aiohttp_client):
    client = await aiohttp_client(app_builder())
    with aiohttp.MultipartWriter("form-data") as multipart:
        multipart.append_json(
            {"title": "Les trois petits cochons", "nb_page": "2"},
            headers={
                "Content-Disposition": 'form-data; name="book"',
                "Content-Type": "application/json",
            },
        )
        multipart.append(
            "Chapitre 1: Maison en paille ...",
            headers={
                "Content-Disposition": 'form-data; name="page_1"; filename="chap1.txt"'
            },
        )

        resp = await client.post("/book-and-files", data=multipart)

    assert resp.status == 400
    assert await resp.json() == [
        {
            "in": "body",
            "loc": ["__root__"],
            "msg": 'The required part named "page_2" is not provided in the multipart request',
            "type": "type_error.multipart",
        }
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_send_standard_request_instead_of_multipart(app_builder, aiohttp_client):
    client = await aiohttp_client(app_builder())
    resp = await client.post(
        "/book-and-files", json={"title": "Les trois petits cochons", "nb_page": "2"}
    )

    assert resp.status == 400
    assert await resp.json() == [
        {
            "in": "body",
            "loc": ["__root__"],
            "msg": "Multipart request is required",
            "type": "type_error.multipart",
        }
    ]


@pytest.mark.parametrize(
    "app_builder", app_builders_1, ids=["pydantic view", "decorated handler"]
)
async def test_handler_programmed_with_reading_order_error(app_builder, aiohttp_client):
    client = await aiohttp_client(app_builder())
    with aiohttp.MultipartWriter("form-data") as multipart:
        multipart.append(
            "Chapitre 1: Maison en paille ...",
            headers={
                "Content-Disposition": 'form-data; name="page_1"; filename="chap1.txt"'
            },
        )
        multipart.append(
            "Chapitre 2: Maison en bois ...",
            headers={
                "Content-Disposition": 'form-data; name="page_2"; filename="chap1.txt"'
            },
        )
        resp = await client.post("/bugged", data=multipart)

    assert resp.status == 500
    assert await resp.json() == {
        "error": 'Try to read part "page_2" before "page_1" in the multipart request'
    }


async def test_error_handler_definition():

    with pytest.raises(RuntimeError) as e_info:

        @inject_params
        async def post_book_and_upload_file(book_1: BookModel, book_2: BookModel):
            return web.json_response({})

    assert (
        str(e_info.value)
        == 'You cannot define multiple bodies arguments with pydantic.BaseModel ("book_1" and "book_2" are annotated with a pydantic.BaseModel)'
    )

    with pytest.raises(RuntimeError) as e_info:

        @inject_params
        async def post_book_and_upload_file(
            page_1: UploadedFile, book: BookModel, page_2: UploadedFile
        ):
            return web.json_response({})

    assert (
        str(e_info.value)
        == 'You cannot define a pydantic.BaseModel argument after an UploadedFile argument. (The argument "book" must be defined before "page_1")'
    )
