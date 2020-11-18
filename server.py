import os
import logging
from aiohttp import web
import aiofiles
import asyncio
import argparse
import itertools
from functools import partial


BASE_DIR = os.path.dirname(os.path.realpath(__file__))

CHUNK_SIZE = 100000

logger = logging.getLogger(__file__)

parser = argparse.ArgumentParser(description='Microservice for download photo archive ')

parser.add_argument('-l',
                    '--logging',
                    action='store_true',
                    default=os.getenv('LOGGING', default=False),
                    help='enable logging; default=False'
                    )

parser.add_argument('--photos_dir',
                    type=str,
                    default=os.getenv('PHOTOS_DIR', default=BASE_DIR + '/test_photos/'),
                    help='',
                    )

parser.add_argument('--delay',
                    type=int,
                    default=os.getenv('DELAY', default=0),
                    help='delay for downloading; default=0',
                    )


async def get_archive_process(file_name, photos_dir):

    if not os.path.exists(os.path.join(photos_dir, file_name)):
        return None
    cmd = ['zip', '-r', '-',  file_name]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=photos_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return proc


async def archivate(photos_dir, delay, request):
    file_name = request.match_info.get('archive_hash')
    
    if not file_name:
        raise web.HTTPBadRequest()

    archive_process = await get_archive_process(file_name, photos_dir)
    if not archive_process:
        raise web.HTTPNotFound(text='Архив не существует или был удален')

    response = web.StreamResponse()

    response.headers['Content-Type'] = 'application/zip'
    response.headers['CONTENT-DISPOSITION'] = f'attachment; filename={file_name}.zip'
    await response.prepare(request)

    try:
        for chunk_number in itertools.count(1):
            data = await archive_process.stdout.read(CHUNK_SIZE)
            if data:
                logger.debug(f'Sending archive chunk {chunk_number} {archive_process.pid}')
                await response.write(data)
            else:
                logger.debug(f'Archivate stopped {archive_process.pid}')
                break

            await asyncio.sleep(delay)

    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.debug('Download was interrupted')
        raise
    finally:
        if archive_process.returncode is None:
            archive_process.kill()
            await archive_process.communicate()
        response.force_close()
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    args = parser.parse_args()
    if args.logging:
        level = logging.DEBUG
    else:
        level = logging.CRITICAL

    photos_dir, delay,  = args.photos_dir, args.delay

    logging.basicConfig(format='%(levelname)-8s [%(asctime)s] %(message)s', level=level)

    archivate_with_params = partial(archivate, photos_dir, delay)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate_with_params),
    ])

    web.run_app(app)
