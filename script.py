import asyncio

import subprocess
from subprocess import PIPE

#subprocess.call("zip -r - ./photos/* | cat > arch.zip")


#subprocess.call(['zip xxx *'])

#subprocess.call(['zip', '-r', 'archive.zip', '/home/kratorr/projects/devman/async_download_service/photos'])

#
#s = subprocess.check_output(['zip', '-r', 'archive.zip', '/home/kratorr/projects/devman/async_download_service/photos'])
#print(s)

async def get_archive_process(path_source_dir):
    cmd = ['zip', '-jr', '-', path_source_dir]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    #data = await proc.stdout.read(100000)


    # Wait for the subprocess exit.
   # await proc.wait()
    
    with open('zxxxx.zip', 'wb+') as f:
        while True:
            data = await proc.stdout.read(100000)
            if data:
                f.write(data)
            else:
                break




loop = asyncio.get_event_loop()
loop.run_until_complete(get_archive_process('/home/kratorr/projects/devman/async_download_service/photos'))
loop.close()