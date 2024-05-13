# MIT License

import enum
from decimal import Decimal

PICO_DIVISOR: Decimal = Decimal(1000000000000)


@enum.unique
class InfoClass(enum.IntEnum):
    "The VRT Information Class"
    SINGLE_SPAN_INT32 = 1
    MULTI_SPAN_INT32 = 2
    SINGLE_SPAN_FREQ_INT32 = 3
    MULTI_SPAN_FREQ_INT32 = 4
    SINGLE_OCTAVE_INT32 = 5
    THIRD_OCTAVE_INT32 = 6
    TIMESTAMP_INT32 = 7
    SYSTEM_CONTEXT = 8
    SINGLE_SPAN_FLOAT32 = 9


@enum.unique
class PacketClass(enum.IntEnum):
    "The VRT Packet Class"
    MEAS_INT32 = 1
    MEAS_INFO = 2
    EX_MEAS_INFO = 3
    FREQ_INT32 = 4
    REAL_FREQ_INT32 = 5
    FREQ_INFO = 6
    SINGLE_OCTAVE_INT32 = 7
    THIRD_OCTAVE_INT32 = 8
    OCTAVE_INFO = 9
    TIMESTAMP_INT32 = 10
    TACH_INFO = 11
    MFUNC_INFO = 12
    MEAS_FLOAT32 = 13


@enum.unique
class PacketType(enum.IntEnum):
    """
    The VRT Packet Type field.
    """

    IF_DATA_NO_ID = 0
    IF_DATA_WITH_ID = 1
    EXT_DATA_NO_ID = 2
    EXT_DATA_WITH_ID = 3
    IF_CONTEXT = 4
    EXT_CONTEXT = 5


@enum.unique
class TimestampInteger(enum.IntEnum):
    """
    The VRT Timestamp Integer field.
    """

    NONE = 0
    UTC = 1
    GPS = 2
    OTHER = 3


@enum.unique
class TimestampFractional(enum.IntEnum):
    """
    The VRT Timestamp Fractional field.
    """

    NONE = 0
    COUNT = 1
    REAL = 2
    FREE = 3


@enum.unique
class TrailerEvents(enum.IntFlag):
    """
    The VRT measurement packet trailer flags.
    """

    USER1 = 1 << 0
    USER2 = 1 << 1
    USER3 = 1 << 2
    USER4 = 1 << 3
    SAMPLE_LOSS = 1 << 4
    OVER_RANGE = 1 << 5
    SPECTRAL_INVERSION = 1 << 6
    DETECTED_SIGNAL = 1 << 7
    AGC_MGC = 1 << 8
    REFERENCE_LOCK = 1 << 9
    VALID_DATA = 1 << 10
    CALIBRATED_TIME = 1 << 11


@enum.unique
class MeasInfoContextIndicator(enum.IntFlag):
    """
    The VRT Measurement Info Context packet's Context Indicator flags.
    """

    FIELD_CHANGED = 0x80000000
    BANDWIDTH = 0x20000000
    REFERENCE_LEVEL = 0x01000000
    OVER_RANGE_COUNT = 0x00400000
    SAMPLE_RATE = 0x00200000
    TEMPERATURE = 0x00040000
    EVENTS = 0x00010000


@enum.unique
class LogicalEvents(enum.IntFlag):
    """
    The VRT Measurement Info Context packet's Event Enables and Indicators fields' flags.
    """

    SAMPLE_LOSS = 1 << 4
    OVER_RANGE = 1 << 5
    SPECTRAL_INV = 1 << 6
    DETECTED_SIG = 1 << 7
    AGC_MGC = 1 << 8
    REF_LOCK = 1 << 9
    VALID_DATA = 1 << 10
    CALIB_TIME = 1 << 11
