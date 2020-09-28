import os
import logging
from aiohttp import web
import aiofiles
import asyncio
import argparse

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

CHUNK_SIZE=100000

logging.basicConfig(format='%(levelname)-8s [%(asctime)s] %(message)s', level=logging.DEBUG)

parser = argparse.ArgumentParser(description='Microservice for download photo archive ')

parser.add_argument('--logging',
                    action='store_true',
                    default=os.getenv('LOGGING', default=True),
                    help='enable logging; default=True'
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


async def get_archive_process(path_source_dir):
    print(os.path.join(args.photos_dir, path_source_dir))
    if not os.path.exists(os.path.join(args.photos_dir, path_source_dir)):
        return None
    cmd = ['zip', '-r', '-',  path_source_dir]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=args.photos_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return proc


async def archivate(request):
    file_name = request.match_info.get('archive_hash')
    archive_proccess = await get_archive_process(file_name)
    if not archive_proccess:
        raise web.HTTPNotFound(text='Архив не существует или был удален')

    response = web.StreamResponse()

    response.headers['Content-Type'] = 'application/zip'
    response.headers['CONTENT-DISPOSITION'] = f'attachment; filename={file_name}.zip'
    await response.prepare(request)

    chunk_number = 1

    try:
        while True:
            data = await archive_proccess.stdout.read(CHUNK_SIZE)
            if data:
                logging.info(f'Sending archive chunk {chunk_number} {archive_proccess.pid}')
                await response.write(data)
            else:
                logging.info(f'Archivate stopped {archive_proccess.pid}')
                break
            chunk_number += 1
            await asyncio.sleep(args.delay)

    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info('Download was interrupted')
        raise
    finally:
        if archive_proccess.returncode is None:
            archive_proccess.kill()
            await archive_proccess.communicate()
        response.force_close()
    return response


async def handle_index_page(request):
    print(args.photos_dir)
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')



if __name__ == '__main__':
    app = web.Application()
    args = parser.parse_args()
    print(args)

    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])

    web.run_app(app)
