# MIT License

# pylint: disable=attribute-defined-outside-init
# mypy: disable-error-code="attr-defined"

from __future__ import annotations

from decimal import Decimal
from datetime import datetime
import struct
import pprint
from typing import ClassVar

from .constants import PICO_DIVISOR
from .constants import InfoClass
from .constants import PacketClass
from .constants import PacketType
from .constants import TimestampInteger
from .constants import TimestampFractional
from .constants import TrailerEvents


class BitField:
    """
    A superclass representing a 32-bit integer broken into specific bit fields.
    """

    _fields_: ClassVar[tuple[tuple[str | None, int], ...]] = tuple()

    def __init__(self, word: int) -> None:
        self.decode(word)

    def encode(self) -> bytes:
        """
        Returns a `bytes` representation of the bitfield.
        """
        return struct.pack("!I", int(self))

    def decode(self, word: int):
        """
        Fill all fields from a `bytes` representation of the bitfield.
        """
        for name, width in self._fields_:
            if name:
                mask = (1 << width) - 1
                setattr(self, name, word & mask)
            word >>= width

    def __str__(self) -> str:
        """
        Returns a human-readable representation of the bitfield.
        """
        fields = []
        for name, _ in self._fields_:
            if name:
                fields.append(f"{name}={getattr(self, name)}")
        return f'{type(self).__name__}(word={hex(int(self))}, {", ".join(fields)})'

    def __int__(self) -> int:
        word: int = 0
        for i, (name, width) in enumerate(reversed(self._fields_)):
            if i > 0:
                word <<= width
            if name:
                word |= getattr(self, name)
        return word


class Header(BitField):
    """
    The header of a VRT packet.

    - size: (16 bits) The total number of 32-bit words in the packet, including this header word.
    - count: (4 bits) The 4-bit sequence number. This should increment separately for each combination of packet_type and stream_id.
    - tsf: (2 bits) The meaning of the fractional portion of the timestamp. Decode with :py:enum:`.constants.TimestampFractional`.
    - tsi: (2 bits) The meaning of the integer portion of the timestamp. Decode with :py:enum:`.constants.TimestampInteger`.
    - tsm: (1 bit) For context packets, indicates whether the timestamp is an exact match for the timestamp in the associated data packet's header (True) or instead represents the precise time of the events specified by the contents of the context packet (False).
    - has_trailer: (1 bit) 1 when a trailer word is included in the packet.
    - has_class_id: (1 bit) 1 when a 2-word class specifier is included in the packet.
    - packet_type: (4 bits) The packet type. Decode with :py:enum:`.constants.PacketClass`.
    """

    _fields_ = (
        ("size", 16),
        ("count", 4),
        ("tsf", 2),
        ("tsi", 2),
        ("tsm", 1),
        (None, 1),
        ("has_trailer", 1),
        ("has_class_id", 1),
        ("packet_type", 4),
    )


class TrailerFields(BitField):
    """
    The trailer fields of a VRT packet.

    - context_count: (7 bits) The number of context packets associated with this data packet.
    - context_en: (1 bit) 1 when context data is enabled for this information stream.
    - indicators: (12 bits) The trailer flag indicators. Use :py:enum:`.constants.TrailerEvents` to decode this value.
    - enables: (12 bits) The trailer flag enables. Use :py:enum:`.constants.TrailerEvents` to decode this value. When a bit is 1, the corresponding bit in `indicators` is valid and should be read.
    """

    _fields_ = (
        ("context_count", 7),
        ("context_en", 1),
        ("indicators", 12),
        ("enables", 12),
    )


class Trailer:
    """
    Represents a VRT Packet Trailer.

    Args:
        context_count: The number of context packets associated with this packet.
        enables: If a flag is set in this mask, the corresponding bit in `indicators` is enabled and should be checked.
        indicators: A mask representing various status conditions. Each flag is only valid if the corresponding bit in `enables` is set.
    """

    def __init__(
        self,
        context_count: int,
        enables: TrailerEvents,
        indicators: TrailerEvents,
    ):
        self.context_count = context_count
        self.enables = enables
        self.indicators = indicators

    def encode(self) -> int:
        """
        Convert the trailer back into the raw unsigned integer format.
        """

        trailer = TrailerFields(0)
        if self.context_count is not None:
            trailer.context_en = 1
            trailer.context_count = self.context_count
        trailer.enables = int(self.enables)
        trailer.indicators = int(self.indicators)
        return int(trailer)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"Trailer(context_count={self.context_count}, enables={self.enables}, indicators={self.indicators})"

    @staticmethod
    def decode(word: int) -> Trailer:
        """
        Create a new `Trailer` from an unsigned 32-bit integer value.

        Args:
            word: The raw packet data, as an unsigned 32-bit integer.
        """

        trailer = TrailerFields(word)
        enables = TrailerEvents(trailer.enables)
        indicators = TrailerEvents(trailer.indicators)

        if trailer.context_en:
            count = trailer.context_count
        else:
            count = None

        return Trailer(count, enables, indicators)


class Packet:
    """
    A VRT packet.

    Args:
        packet_type: The packet type.
        tsi: The meaning of the integer portion of the timestamp.
        tsf: The meaning of the fractional portion of the timestamp.
        count: The 4-bit sequence number. This should increment separately for each combination of packet_type and stream_id.
        stream_id: The unique numerical identifier of this data stream.
        timestamp: The value of the timestamp fields.
        oui: The IANI OUI of the vendor of the product that created this packet.
        info_class: The class of the information stream that this packet belongs to.
        packet_class: The class of the packet.
        data: The payload of the packet.
        trailer: The parsed information from the packet trailer.
    """

    def __init__(
        self,
        packet_type: PacketType,
        tsi: TimestampInteger,
        tsf: TimestampFractional,
        count: int,
        stream_id: int | None = None,
        timestamp: Decimal | datetime | None = None,
        oui: int | None = None,
        info_class: InfoClass | int | None = None,
        packet_class: PacketClass | int | None = None,
        data: bytes | None = None,
        trailer: Trailer | None = None,
        tsm: bool | None = None,
    ) -> None:
        self.stream_id = stream_id
        self.count = count
        self.packet_type = packet_type
        self.tsi = tsi
        self.tsf = tsf
        self.tsm = tsm
        self.timestamp: Decimal | None = _parse_timestamp(timestamp)
        self.oui = oui
        self.info_class = info_class
        self.packet_class = packet_class
        self.data: bytes = data or bytes()
        self.trailer = trailer

    @property
    def header(self) -> Header:
        header = Header(0)

        header.packet_type = int(self.packet_type)
        header.tsi = int(self.tsi)
        header.tsf = int(self.tsf)
        header.count = self.count
        header.tsm = int(self.tsm or 0)
        header.has_class_id = self.has_class_id
        header.has_trailer = self.has_trailer
        header.size = self.packet_size

        return header

    @property
    def packet_size(self) -> int:
        packet_size: int = 1

        if self.has_stream_id:
            packet_size += 1

        if self.has_class_id:
            packet_size += 2

        if self.tsi != TimestampInteger.NONE:
            packet_size += 1

        if self.tsf != TimestampFractional.NONE:
            packet_size += 2

        packet_size += len(self.data) // 4

        if self.has_trailer:
            packet_size += 1

        return packet_size

    @property
    def has_stream_id(self) -> bool:
        # TBM: not sure about other types
        return self.packet_type == PacketType.IF_DATA_WITH_ID

    @property
    def has_class_id(self) -> bool:
        return None not in (
            self.oui,
            self.info_class,
            self.packet_class,
        )

    @property
    def class_id(self) -> bytes | None:
        if not self.has_class_id:
            return None

        assert self.info_class is not None
        assert self.packet_class is not None

        return struct.pack(
            "!IHH",
            self.oui,
            int(self.info_class),
            int(self.packet_class),
        )

    @property
    def integer_seconds_timestamp(self) -> int | None:
        if self.tsi == TimestampInteger.NONE:
            return None

        assert self.timestamp is not None
        return int(self.timestamp)

    @property
    def fractional_seconds_timestamp(self) -> int | None:
        if self.tsf == TimestampFractional.NONE:
            return None

        assert self.timestamp is not None
        assert self.integer_seconds_timestamp is not None
        return int((self.timestamp - self.integer_seconds_timestamp) * PICO_DIVISOR)

    @property
    def has_trailer(self) -> bool:
        return self.trailer is not None

    def __repr__(self):
        return f"""Packet(stream_id={self.stream_id}, count={self.count}, packet_type={str(self.packet_type)},
             tsi={str(self.tsi)}, tsf={str(self.tsf)}, tsm={self.tsm}, timestamp={self.timestamp},
             oui={hex(self.oui) if self.oui is not None else None}, info_class={str(self.info_class) if self.info_class is not None else None}, packet_class={str(self.packet_class) if self.packet_class is not None else None},
             data={pprint.pformat(self.data, compact=True)},
             trailer={pprint.pformat(self.trailer, compact=True)}
        """

    def encode(self) -> bytearray:
        """
        Encode the packet`.

        Returns:
            The encoded packet.
        """

        buffer = bytearray()

        buffer += struct.pack("!I", int(self.header))

        if self.has_stream_id:
            assert self.stream_id is not None
            buffer += struct.pack("!I", self.stream_id)

        if self.has_class_id:
            assert self.class_id is not None
            buffer += self.class_id

        if self.tsi != TimestampInteger.NONE:
            assert self.integer_seconds_timestamp is not None
            buffer += struct.pack("!I", self.integer_seconds_timestamp)

        if self.tsf != TimestampFractional.NONE:
            assert self.fractional_seconds_timestamp is not None
            buffer += struct.pack("!Q", self.fractional_seconds_timestamp)

        buffer += self.data

        if self.has_trailer:
            assert self.trailer is not None
            buffer += struct.pack("!I", self.trailer.encode())

        return buffer


def _parse_timestamp(timestamp: Decimal | datetime | None) -> Decimal | None:
    """
    Parse a timestamp into a `Decimal` value.

    Args:
        timestamp: The timestamp to parse.

    Returns:
        The parsed timestamp as a `Decimal` value, or `None` if the timestamp is `None`.
    """

    if timestamp is None:
        return None

    if isinstance(timestamp, Decimal):
        return timestamp

    return Decimal(timestamp.timestamp())
