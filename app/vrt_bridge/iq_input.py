# MIT License

from __future__ import annotations

import pathlib
from queue import Queue
from threading import Thread
import asyncio
import abc
from collections.abc import Generator

import numpy as np

from aioprocessing import AioQueue

from vrt_bridge.connectors import Connector
from vrt_bridge.connectors.connector_base import ConnectorBase

from vrt_bridge.process import Process
from vrt_bridge.utilities import load_iq_samples_from_wav
from vrt_bridge.logging import logger


class IQInputProcess(Process):
    """
    Process handling the IQ input.
    """

    def __init__(
        self,
        iq_input: IQInputBase,
        output_queue: AioQueue,
    ) -> None:
        super().__init__()

        self._iq_input: IQInputBase = iq_input
        self._output_queue: AioQueue = output_queue

    @staticmethod
    def load(
        configuration: dict,
        output_queue: AioQueue,
    ) -> IQInputProcess:
        return IQInputProcess(
            iq_input=IQInput.load(configuration),
            output_queue=output_queue,
        )

    def _run(self) -> None:
        with self._iq_input:
            for data in self._iq_input.receive():
                self._output_queue.put(data)


class IQInput:
    @staticmethod
    def load(configuration: dict) -> IQInputBase:
        match configuration["type"].lower():
            case "endpoint":
                return IQEndpoint.load(configuration["endpoint"])

            case "file":
                return IQFile.load(configuration["file"])

            case _:
                raise NotImplementedError


class IQInputBase(Thread, abc.ABC):
    def __init__(
        self,
        bit_resolution: int,
        queue_size: int | None,
    ) -> None:
        super().__init__()
        self._bit_resolution: int = bit_resolution
        self._queue_size: int | None = queue_size

    @property
    def bit_resolution(self) -> int:
        return self._bit_resolution

    @property
    def queue_size(self) -> int | None:
        return self._queue_size

    @abc.abstractmethod
    def run(self) -> None: ...

    @abc.abstractmethod
    def receive(self) -> Generator[np.ndarray, None, None]: ...

    def __enter__(self) -> IQInputBase:
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.join()


class IQEndpoint(IQInputBase):
    def __init__(
        self,
        connector: ConnectorBase,
        bit_resolution: int,
        queue_size: int | None,
    ) -> None:
        super().__init__(
            bit_resolution=bit_resolution,
            queue_size=queue_size,
        )

        self._connector: ConnectorBase = connector
        self._queue: Queue = Queue()

    def run(self) -> None:
        asyncio.run(self._run())

    def receive(self) -> Generator[np.ndarray, None, None]:
        sample_size: int = self.bit_resolution * 2 // 8
        try:
            buffer: bytes = bytes()
            while True:
                buffer += self._queue.get()
                if buffer and len(buffer) % sample_size == 0:
                    yield np.frombuffer(
                        buffer, dtype=_type_from_bit_resolution(self.bit_resolution)
                    ).astype(np.int16).reshape(-1, 2)
                    buffer = bytes()

        except Exception as exc:
            logger.exception(exc)
            raise exc

    def __str__(self) -> str:
        return f"I/Q Endpoint [{self._connector}]"

    @staticmethod
    def load(configuration: dict) -> IQEndpoint:
        return IQEndpoint(
            connector=Connector.load(configuration),
            bit_resolution=configuration["bit_resolution"],
            queue_size=configuration.get("queue_size"),
        )

    async def _run(self) -> None:
        async with self._connector:
            async for packet in self._connector.subscribe(queue_size=self._queue_size):
                self._queue.put(packet)


class IQFile(IQInputBase):
    def __init__(
        self,
        format: str,
        file_path: pathlib.Path,
        start_offset: float,
        duration: float,
        sample_count: int,
        bit_resolution: int,
        queue_size: int | None,
    ) -> None:
        super().__init__(
            bit_resolution=bit_resolution,
            queue_size=queue_size,
        )

        if format != "wav":
            raise NotImplementedError("Only WAV files are supported.")

        self._format: str = format
        self._file_path: pathlib.Path = file_path
        self._start_offset: float = start_offset
        self._duration: float = duration
        self._sample_count: int = sample_count
        self._iq_sample_generator: Generator[np.ndarray, None, None] | None = None

    def run(self) -> None:
        self._iq_sample_generator = load_iq_samples_from_wav(
            wav_file_path=self._file_path,
            block_size=self._sample_count,
            start_offset=self._start_offset,
            duration=self._duration,
        )

    def receive(self) -> Generator[np.ndarray, None, None]:
        assert self._iq_sample_generator is not None
        for iq_samples in self._iq_sample_generator:
            yield iq_samples.astype(_type_from_bit_resolution(self.bit_resolution))

    def __str__(self) -> str:
        return f"I/Q File ({self._format}) [{self._file_path}]"

    @staticmethod
    def load(configuration: dict) -> IQFile:
        return IQFile(
            format=configuration["format"],
            file_path=configuration["file_path"],
            start_offset=configuration.get("start_offset", 0),
            duration=configuration.get("duration", None),
            sample_count=configuration["sample_count"],
            bit_resolution=configuration["bit_resolution"],
            queue_size=configuration.get("queue_size"),
        )


def _type_from_bit_resolution(bit_resolution: int) -> type[np.signedinteger]:
    match bit_resolution:
        case 8:
            return np.int8
        case 12 | 16:
            return np.int16
        case 24 | 32:
            return np.int32
        case 64:
            return np.int64
        case _:
            raise NotImplementedError
