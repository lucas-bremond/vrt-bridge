# MIT License

from aioprocessing import AioQueue

from .iq_input import IQInputProcess
from .vrt_output import VRTOutputProcess
from .packetizer import PacketizerProcess


def main(configuration: dict) -> None:
    iq_queue: AioQueue = AioQueue(maxsize=10000)
    vrt_queue: AioQueue = AioQueue(maxsize=10000)

    iq_input_process = IQInputProcess.load(
        configuration=configuration["iq_input"],
        output_queue=iq_queue,
    )

    packetizer_process = PacketizerProcess.load(
        configuration=configuration["packetizer"],
        input_queue=iq_queue,
        output_queue=vrt_queue,
    )

    vrt_output_process = VRTOutputProcess.load(
        configuration=configuration["vrt_output"],
        input_queue=vrt_queue,
    )

    iq_input_process.start()
    packetizer_process.start()
    vrt_output_process.start()

    iq_input_process.join()
    packetizer_process.join()
    vrt_output_process.join()
