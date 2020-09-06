import os
import logging
from aiohttp import web
import aiofiles
import asyncio

import datetime

INTERVAL_SECS = 1

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(format='%(levelname)-8s [%(asctime)s] %(message)s', level=logging.DEBUG, filename='server.log')


async def get_archive_process(path_source_dir):
    if not os.path.exists(BASE_DIR + '/test_photos/' + path_source_dir):
        return None
    cmd = ['zip', '-r', '-',  path_source_dir]
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd="./test_photos",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return proc


async def uptime_handler(request):
    file_name = request.match_info.get('archive_hash')
    response = web.StreamResponse()

    response.headers['Content-Type'] = 'text/html'
    await response.prepare(request)

    while True:
        formatted_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f'{formatted_date} + {file_name} + <br>'  # <br> — HTML тег переноса строки

        await response.write(message.encode('utf-8'))

        await asyncio.sleep(INTERVAL_SECS)


async def archivate(request):
    file_name = request.match_info.get('archive_hash')
    archive = await get_archive_process(file_name)
    if not archive:
        raise web.HTTPNotFound(text='Архив не существует или был удален')

    response = web.StreamResponse()

    response.headers['Content-Type'] = 'application/zip'
    response.headers['CONTENT-DISPOSITION'] = f'attachment; filename={file_name}.zip'
    await response.prepare(request)

    chunk_number = 1
    while True:

        data = await archive.stdout.read(4096)
        if data:
            logging.info(f'Sending archive chunk {chunk_number}')
            await response.write(data)
        else:
            break
        chunk_number += 1
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])

    web.run_app(app)
