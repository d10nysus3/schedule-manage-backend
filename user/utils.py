import json
from typing import Callable

from django.http import HttpRequest, HttpResponse


def post_test(handle: Callable[[HttpRequest], HttpResponse]) -> Callable[[HttpRequest], HttpResponse]:
    def h(req: HttpRequest) -> HttpResponse:
        if req.method == 'POST':
            req_body = req.body
            try:
                parse = {} if len(req_body) == 0 else json.loads(req.body)
                print(f'Request Body: {parse}')

            except json.JSONDecodeError:
                print(f'请求体解析错误: {req_body}')
            except KeyError:
                print(f'请求体非法: {req_body}')
        return handle(req)

    return h
