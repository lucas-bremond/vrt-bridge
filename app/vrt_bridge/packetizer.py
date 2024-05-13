# MIT License

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
import multiprocessing
from queue import Full

from aioprocessing import AioQueue

from vrt_bridge.vita.vrt import Packet
from vrt_bridge.vita.vrt import constants

from vrt_bridge.utilities import generate_iq_sample_block
from vrt_bridge.utilities import pack_least_significant_12_bits
from vrt_bridge.utilities import generate_context_packet
from vrt_bridge.utilities import limit_call_frequency
from vrt_bridge.utilities import measure_throughput
from vrt_bridge.process import Process
from vrt_bridge.logging import logger


class PacketizerProcess(Process):
    """
    Process handling the packetizer.
    """

    def __init__(
        self,
        frequency: int,
        bandwidth: int,
        sample_rate: int,
        sample_count: int,
        context_emission_frequency: float,
        queue_size: int,
        input_queue: AioQueue,
        output_queue: AioQueue,
    ) -> None:
        super().__init__()

        self._frequency: int = frequency  # [Hz]
        self._bandwidth: int = bandwidth  # [Hz]
        self._sample_rate: int = sample_rate  # [baud]
        self._sample_count: int = sample_count
        self._context_emission_frequency: float = context_emission_frequency  # [Hz]

        self._input_queue: AioQueue = input_queue
        self._output_queue: AioQueue = output_queue

        self._internal_queue: multiprocessing.Queue = multiprocessing.Queue(
            maxsize=queue_size
        )

    @staticmethod
    def load(
        configuration: dict,
        input_queue: AioQueue,
        output_queue: AioQueue,
    ) -> PacketizerProcess:
        return PacketizerProcess(
            frequency=configuration["frequency"],
            bandwidth=configuration["bandwidth"],
            sample_rate=configuration["sample_rate"],
            sample_count=configuration["sample_count"],
            context_emission_frequency=configuration["context_emission_frequency"],
            queue_size=configuration["queue_size"],
            input_queue=input_queue,
            output_queue=output_queue,
        )

    def _run(self) -> None:
        handle_packetization_process = multiprocessing.Process(
            target=self._handle_packetization,
        )

        handle_data_packet_output_process = multiprocessing.Process(
            target=self._handle_data_packet_output,
        )

        handle_context_process = multiprocessing.Process(
            target=self._handle_context,
        )

        handle_packetization_process.start()
        handle_data_packet_output_process.start()
        handle_context_process.start()

        handle_packetization_process.join()
        handle_data_packet_output_process.join()
        handle_context_process.join()

    def _handle_packetization(self) -> None:
        start_timestamp: datetime = datetime.now(timezone.utc)
        count: int = 0

        for iq_sample_block in generate_iq_sample_block(
            queue=self._input_queue,
            block_size=self._sample_count,
        ):
            # TBM: Fields should be configurable (currently, hardcoded)
            vrt_packet = Packet(
                packet_type=constants.PacketType.IF_DATA_WITH_ID,
                tsi=constants.TimestampInteger.OTHER,
                tsf=constants.TimestampFractional.REAL,
                count=count % 16,
                stream_id=0,
                oui=0x7C386C,
                info_class=22065,
                packet_class=count % 16,
                timestamp=(
                    start_timestamp
                    + timedelta(seconds=count * self._sample_count / self._sample_rate)
                ),
                data=pack_least_significant_12_bits(iq_sample_block),
            )

            # logger.debug(f"Packetized {vrt_packet}")

            count += 1

            _maybe_enqueue(self._internal_queue, vrt_packet.encode(), "internal_queue")

    def _handle_data_packet_output(self) -> None:
        call_delay: float = self._sample_count / self._sample_rate

        @limit_call_frequency(call_delay)
        def send_packet(packet: bytes):
            _maybe_enqueue(self._output_queue, packet, "output_queue")

        data_size: int = self._sample_count * 2 * 12 // 8  # [bytes]

        while True:
            packet: bytes = self._internal_queue.get()

            send_packet(packet)

            measure_throughput(data_size)

    def _handle_context(self) -> None:
        if self._context_emission_frequency <= 0.0:
            return

        sleep: float = 1.0 / self._context_emission_frequency

        while True:
            context_packet: bytes = generate_context_packet(
                bandwidth=self._bandwidth,
                sample_rate=self._sample_rate,
                frequency=self._frequency,
            )

            _maybe_enqueue(self._output_queue, context_packet, "output_queue")

            time.sleep(sleep)


def _maybe_enqueue(
    queue: multiprocessing.Queue | AioQueue,
    item,
    queue_name: str,
) -> None:
    try:
        queue.put(item, block=True)

    except Full:
        logger.warning(f"Queue [{queue_name}] is full, dropping item...")
