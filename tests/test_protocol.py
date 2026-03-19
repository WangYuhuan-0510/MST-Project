# 协议帧打包/解析、校正和错误
import pytest

from mst.device.protocol import ProtocolFrame


def test_protocol_roundtrip():
    frame = ProtocolFrame(command=0x10, payload=b"\x01\x02")
    raw = frame.to_bytes()
    parsed = ProtocolFrame.parse(raw)
    assert parsed.command == 0x10
    assert parsed.payload == b"\x01\x02"


def test_protocol_bad_checksum():
    frame = ProtocolFrame(command=0x10, payload=b"\x01\x02")
    raw = bytearray(frame.to_bytes())
    raw[-1] ^= 0xFF
    with pytest.raises(ValueError):
        ProtocolFrame.parse(bytes(raw))

