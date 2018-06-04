import asyncio
import json
import shlex

from balto.runners.base import BaseRunner


async def _read_stream(stream, cb):
    while True:
        line = await stream.readline()
        if line:
            await cb(line)
        elif stream.at_eof():
            break


class SubprocessRunnerSession(BaseRunner):
    async def run(self):
        cmd, args = self.command

        final_cmd = "%s %s" % (cmd, shlex.quote(args))

        await self.launch_cmd(final_cmd)

    async def launch_cmd(self, cmd):
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_directory,
            loop=self.loop,
        )

        await asyncio.gather(
            _read_stream(process.stdout, self.read_line),
            _read_stream(process.stderr, self.read_line),
        )

        return_code = await process.wait()

        if return_code != 0:
            print("cmd exited with return code: %r" % return_code)

        return return_code
