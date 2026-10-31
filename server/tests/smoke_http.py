"""Exercise actual MCP initialization, tool discovery, and calls over local HTTP."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from server.tests.test_knowledge import fixture


async def main():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'knowledge.json'
        path.write_bytes(Path(os.environ['FEMORA_SMOKE_KNOWLEDGE']).read_bytes() if os.environ.get('FEMORA_SMOKE_KNOWLEDGE') else fixture())
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = {**os.environ, 'FEMORA_KNOWLEDGE_FILE': str(path)}
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server.app:app', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f'http://127.0.0.1:{port}'
            async with httpx.AsyncClient() as http:
                for _ in range(100):
                    try:
                        response = await http.get(base + '/healthz')
                        if response.status_code == 200:
                            break
                    except httpx.ConnectError:
                        pass
                    if process.poll() is not None:
                        raise RuntimeError('Server exited before readiness')
                    await asyncio.sleep(.1)
                else:
                    raise RuntimeError('Server did not become ready')
                assert (await http.get(base + '/.well-known/openai-apps-challenge')).status_code == 404
            async with streamablehttp_client(base + '/mcp') as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert {t.name for t in tools.tools} == {'search_femora','get_femora_api','read_femora_reference'}
                    for tool in tools.tools:
                        assert tool.annotations.readOnlyHint is True
                        assert tool.annotations.destructiveHint is False
                        assert tool.annotations.openWorldHint is False
                    result = await session.call_tool('get_femora_api', {'symbol':'model.material.nd.elastic_isotropic'})
                    assert not result.isError and result.structuredContent['found'] is True
                    missing = await session.call_tool('get_femora_api', {'symbol':'model.material.nd.magic_soil'})
                    assert not missing.isError and missing.structuredContent['found'] is False
                    searched = await session.call_tool('search_femora', {'query':'elastic_isotropic'})
                    reference = searched.structuredContent['results'][0]['reference']
                    text = await session.call_tool('read_femora_reference', {'reference':reference,'max_chars':30})
                    assert len(text.structuredContent['content']) == 30
                    rejected = await session.call_tool('read_femora_reference', {'reference':'../../etc/passwd'})
                    assert rejected.isError
            print('MCP HTTP smoke test passed: initialization, annotations, search, exact lookup, pagination, and path rejection.')
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    asyncio.run(main())
