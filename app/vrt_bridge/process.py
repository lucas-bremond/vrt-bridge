# MIT License

from __future__ import annotations

import abc

from aioprocessing.process import AioProcess


class Process(abc.ABC):
    """
    Process base class.
    """

    def __init__(self) -> None:
        super().__init__()
        self._process: AioProcess | None = None

    def start(self) -> None:
        assert self._process is None
        self._process = AioProcess(target=self._run)
        self._process.start()

    def join(self) -> None:
        assert self._process is not None
        self._process.join()
        self._process = None

    @abc.abstractmethod
    def _run(self) -> None:
        raise NotImplementedError
