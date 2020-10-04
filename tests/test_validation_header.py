from aiohttp import web
from aiohttp_pydantic import PydanticView
from datetime import datetime
import json


class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


class ArticleView(PydanticView):

    async def get(self, *, signature_expired: datetime):
        return web.json_response({'signature': signature_expired}, dumps=JSONEncoder().encode)


async def test_get_article_without_required_header_should_return_an_error_message(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view('/article', ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get('/article', headers={})
    assert resp.status == 400
    assert resp.content_type == 'application/json'
    assert await resp.json() == [{'loc': ['signature_expired'],
                                  'msg': 'field required',
                                  'type': 'value_error.missing'}]


async def test_get_article_with_wrong_header_type_should_return_an_error_message(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view('/article', ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get('/article', headers={'signature_expired': 'foo'})
    assert resp.status == 400
    assert resp.content_type == 'application/json'
    assert await resp.json() == [{'loc': ['signature_expired'],
                                  'msg': 'invalid datetime format',
                                  'type': 'value_error.datetime'}]


async def test_get_article_with_valid_header_should_return_the_parsed_type(aiohttp_client, loop):
    app = web.Application()
    app.router.add_view('/article', ArticleView)

    client = await aiohttp_client(app)
    resp = await client.get('/article', headers={'signature_expired': '2020-10-04T18:01:00'})
    assert resp.status == 200
    assert resp.content_type == 'application/json'
    assert await resp.json() == {'signature': '2020-10-04T18:01:00'}
