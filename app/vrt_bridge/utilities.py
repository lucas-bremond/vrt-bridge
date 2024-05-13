# MIT License

import time
from datetime import datetime, timezone, timedelta
import pathlib
import socket
from dataclasses import dataclass
from collections.abc import Generator

import numpy as np

from vrt_bridge.vita.vrt import Packet
from vrt_bridge.vita.vrt import constants

from vrt_bridge.logging import logger


@dataclass
class Scenario:
    name: str
    bandwidth: int
    sample_rate: int
    iq_samples: Generator[np.ndarray, None, None]


def load_iq_samples_from_wav(
    wav_file_path: pathlib.Path | str,
    block_size: int,
    start_offset: float | None = None,
    duration: float | None = None,
    loop: bool = True,
) -> Generator[np.ndarray, None, None]:
    import scipy.io.wavfile as wav

    sample_rate, data = wav.read(wav_file_path)

    start_sample: int = int(start_offset * sample_rate) if start_offset else 0
    end_sample: int = (
        (start_sample + int(duration * sample_rate)) if duration else len(data)
    )

    data = data[start_sample:end_sample]

    # Number of blocks
    block_count: int = (
        data.shape[0] // block_size
        if data.shape[0] % block_size == 0
        else data.shape[0] // block_size + 1
    )

    # Split the array into blocks
    blocks = np.array_split(data, block_count)

    while True:
        for block in blocks:
            yield block

        if not loop:
            break


def generate_iq_sample_block(
    queue,
    block_size: int,
) -> Generator[np.ndarray, None, None]:
    """
    Generator that yields fixed-size byte arrays from a queue.
    """

    block: np.ndarray = np.empty((0, 2), dtype=np.int16)
    while True:
        item = queue.get()
        block = np.concatenate((block, item))

        while len(block) >= block_size:
            # If there is enough data for a complete block, yield it
            # and keep the remainder for the next block.
            yield block[:block_size]
            block = block[block_size:]


def pack_iq_sample_block(
    iq_sample_blocks: Generator[np.ndarray, None, None]
) -> Generator[bytes, None, None]:
    for iq_sample_block in iq_sample_blocks:
        yield pack_least_significant_12_bits(iq_sample_block)


previous_time = None
current_index = 0


def measure_throughput(packet_size: int, granularity: int = 100) -> None:
    global previous_time
    global current_index

    current_time = time.perf_counter()
    current_index += 1

    if previous_time is not None:
        throughput: float = packet_size / (current_time - previous_time)

        if current_index > granularity:
            logger.info(f"Throughput: {int(throughput / 1000)} KB/s")
            current_index = 0

    previous_time = current_time


def pack_least_significant_12_bits(iq_samples: np.ndarray) -> bytes:
    """
    Pack a list of integers into a bytearray,
    keeping only the least significant 12 bits of each integer.

    Args:
        integers: A list of integers to pack.

    Returns:
        A bytearray containing the packed integers.
    """

    # Apply bitmask to retain 12 least significant bits
    converted_iq_samples = (iq_samples & 0xFFF).astype(np.uint32)

    # Shift first elements 12 bits to the left and combine with second elements
    combined_iq_samples = (converted_iq_samples[:, 0] << 12) | converted_iq_samples[:, 1]

    # Convert each combined 24 bit value into 3 bytes and concatenate everything into a single bytes object
    return b"".join(
        combined_iq_sample.byteswap().tobytes()[1:4]
        for combined_iq_sample in combined_iq_samples
    )


def unpack_12_bit_integers(buffer) -> list[int]:
    integers: list[int] = []

    # We're unpacking two 12-bit values from three bytes, so we process three bytes at a time
    for i in range(0, len(buffer), 3):
        # get three bytes, if there's less than three left, the rest becomes 0
        byte1 = buffer[i]
        byte2 = buffer[i + 1] if i + 1 < len(buffer) else 0
        byte3 = buffer[i + 2] if i + 2 < len(buffer) else 0

        # combine three bytes into 24 bits, then split it into two 12-bit integers
        # and append them to our list
        combined = (byte1 << 16) | (byte2 << 8) | byte3
        int1 = (combined >> 12) & 0xFFF  # first 12-bit integer
        int2 = combined & 0xFFF  # second 12-bit integer

        integers.append(int1)
        if i + 2 < len(
            buffer
        ):  # only append the second integer if we had a full three bytes
            integers.append(int2)

    return integers


def limit_call_frequency(min_seconds_between_calls):
    def decorator(func):
        last_called: list[float | None] = [None]

        min_nanoseconds_between_calls = min_seconds_between_calls * 1e9

        def wrapper(*args, **kwargs):
            nonlocal last_called
            if last_called[0] is not None:
                elapsed_time = time.perf_counter_ns() - last_called[0]
                wait_time = min_nanoseconds_between_calls - elapsed_time
                if wait_time > 0:
                    time.sleep(wait_time / 1e9)
            ret = func(*args, **kwargs)
            last_called[0] = time.perf_counter_ns()
            return ret

        return wrapper

    return decorator


def generate_context_packet(
    bandwidth: int,
    sample_rate: int,
    frequency: int,
) -> bytes:
    """
    This function generates a context VRT packet.

    The format of this packet is not fully known: it has been inferred from collecting
    SpectralNet's output and comparing it to the VRT specification.

    Reference packet: 39A180000000007A12000000000000000000000000017EE6760000000000E30000001F800000008954400000A0000000A00002CB00000000
    """

    vrt_packet = Packet(
        packet_type=constants.PacketType.IF_CONTEXT,
        tsi=constants.TimestampInteger.OTHER,
        tsf=constants.TimestampFractional.REAL,
        count=1,
        stream_id=0,
        oui=0x7C386C,
        info_class=0,
        packet_class=0,
        timestamp=datetime.now(timezone.utc),
        data=bytes.fromhex(
            "39A18000000"
            + bandwidth.to_bytes(length=4, byteorder="big").hex().upper()
            + "000000000000000000000000"
            + frequency.to_bytes(length=4, byteorder="big").hex().upper()
            + "000000000E30000001F80000"
            + sample_rate.to_bytes(length=4, byteorder="big").hex().upper()
            + "00000A0000000A00002CB00000000"
        ),
    )

    return (
        bytes.fromhex("49E1001500000000007C386C00000000")  # Header + Stream ID + Class ID
        + vrt_packet.encode()[12:]
    )


def generate(
    queue,
    iq_samples,
    sample_rate: int,
    sample_count: int,
) -> None:
    count: int = 0

    start_timestamp: datetime = datetime.now(timezone.utc)

    for packed_iq_samples in pack_iq_sample_block(iq_samples):
        vrt_packet = Packet(
            packet_type=constants.PacketType.IF_DATA_WITH_ID,
            tsi=constants.TimestampInteger.OTHER,
            tsf=constants.TimestampFractional.REAL,
            count=count % 16,
            stream_id=0,
            oui=0x7C386C,
            info_class=22065,
            packet_class=count % 16,
            timestamp=start_timestamp
            + timedelta(seconds=count * sample_count / sample_rate),
            data=packed_iq_samples,
        )

        count += 1

        encoded_packet: bytes = vrt_packet.encode()

        queue.put(encoded_packet)


def send(
    queue,
    udp_ip_address: str,
    udp_port: str,
    frequency: int,
    bandwidth: int,
    sample_rate: int,
    sample_count: int,
    data_size: int,
) -> None:
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        context_packet: bytes = generate_context_packet(bandwidth, sample_rate, frequency)
        udp_socket.sendto(context_packet, (udp_ip_address, udp_port))

        call_delay: float = sample_count / sample_rate

        @limit_call_frequency(call_delay)
        def send_packet(packet):
            udp_socket.sendto(packet, (udp_ip_address, udp_port))

        while True:
            packet = queue.get()

            send_packet(packet)

            measure_throughput(data_size)

    finally:
        udp_socket.close()
