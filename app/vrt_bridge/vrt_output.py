# MIT License

from __future__ import annotations

import asyncio

from aioprocessing import AioQueue

from vrt_bridge.utilities.handler import Handler

from vrt_bridge.connectors import Connector
from vrt_bridge.connectors.connector_base import ConnectorBase

from vrt_bridge.process import Process


class VRTOutputProcess(Process):
    """
    Process handling the VRT endpoint.
    """

    def __init__(
        self,
        vrt_output: VRTOutput,
        input_queue: AioQueue,
    ) -> None:
        super().__init__()

        self._vrt_output: VRTOutput = vrt_output
        self._input_queue: AioQueue = input_queue

    @staticmethod
    def load(
        configuration: dict,
        input_queue: AioQueue,
    ) -> VRTOutputProcess:
        return VRTOutputProcess(
            vrt_output=VRTOutput.load(configuration),
            input_queue=input_queue,
        )

    def _run(self) -> None:
        asyncio.run(self._handle())

    async def _handle(self) -> None:
        await asyncio.gather(
            self._handle_vrt_output(),
            self._handle_vrt_output_input(),
        )

    async def _handle_vrt_output(self) -> None:
        async with self._vrt_output:
            await self._vrt_output.wait_until_complete()

    async def _handle_vrt_output_input(self) -> None:
        while True:
            data: bytes = await self._input_queue.coro_get()
            await self._vrt_output.send(data)


class VRTOutput(Handler):
    def __init__(
        self,
        connector: ConnectorBase,
    ) -> None:
        super().__init__()

        self._connector: ConnectorBase = connector

    async def send(self, data: bytes) -> None:
        if self._connector.is_active():
            await self._connector.send_packet(data)

    def __str__(self) -> str:
        return f"I/Q Endpoint [{self._connector}]"

    @staticmethod
    def load(configuration: dict) -> VRTOutput:
        return VRTOutput(
            connector=Connector.load(configuration),
        )

    async def _handle(self) -> None:
        async with self._connector:
            self._ready()
            await self.wait_until_complete()
