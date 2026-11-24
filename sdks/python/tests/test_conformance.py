from __future__ import annotations

import json
import unittest
from pathlib import Path

import streampay
from streampay import (
    ContractError,
    ReadClient,
    ScVal,
    StreamError,
    decode_contract_error,
    decode_stream_pay_event,
)
from streampay._events import canonical
from streampay._xdr import decode_invoke_contract_args


SDKS = Path(__file__).resolve().parents[2]
VECTORS = SDKS / "vectors"
SPEC = json.loads((SDKS / "spec" / "streampay.spec.json").read_text(encoding="utf-8"))


class FixtureTransport:
    def __init__(self, result: str) -> None:
        self.result = result
        self.calls: list[tuple[str, tuple[bytes, ...]]] = []

    def simulate(self, method: str, args) -> str:
        self.calls.append((method, tuple(args)))
        return self.result


def load_vectors() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(VECTORS.glob("*.json"))]


def python_value(value_type, value):
    if isinstance(value_type, dict) and "option" in value_type:
        return None if value is None else python_value(value_type["option"], value)
    if isinstance(value_type, list):
        return [python_value(value_type[1], item) for item in value]
    if isinstance(value_type, str) and value_type in {"u32", "u64", "i32", "i64", "u128", "i128"}:
        return int(value)
    return value


class ConformanceTest(unittest.TestCase):
    def test_every_vector_matches_the_spec_fingerprint(self) -> None:
        vectors = load_vectors()
        self.assertTrue(vectors)
        for vector in vectors:
            with self.subTest(vector=vector["name"]):
                self.assertEqual(vector["specFingerprint"], streampay.SPEC_FINGERPRINT)

    def test_read_results_and_argument_bytes_match_signed_envelopes(self) -> None:
        functions = {function["name"]: function for function in SPEC["functions"] if not function["mutating"]}
        checked = 0
        for vector in load_vectors():
            expected = vector["expected"]
            function = functions.get(expected["transaction"]["function"])
            if function is None or "ok" not in expected["result"]:
                continue
            with self.subTest(vector=vector["name"]):
                args = [python_value(arg["type"], expected["transaction"]["args"][arg["name"]]) for arg in function["args"]]
                builder = getattr(streampay, f"{function['name']}_args")
                envelope = decode_invoke_contract_args(vector["transactionEnvelopeXdr"])
                self.assertEqual(envelope.contract, expected["transaction"]["contract"])
                self.assertEqual(envelope.function, function["name"])
                self.assertEqual(tuple(builder(*args)), envelope.args)

                transport = FixtureTransport(vector["resultXdr"])
                result = getattr(ReadClient(transport), function["name"])(*args)
                self.assertEqual(canonical(result), expected["result"]["ok"])
                self.assertEqual(transport.calls, [(function["name"], envelope.args)])
                checked += 1
        self.assertGreaterEqual(checked, 2)

    def test_all_error_vectors_use_the_canonical_enum(self) -> None:
        checked = 0
        for vector in load_vectors():
            expected = vector["expected"]["result"]
            if "error" not in expected:
                continue
            with self.subTest(vector=vector["name"]):
                error = decode_contract_error(vector["resultXdr"])
                self.assertIsInstance(error, StreamError)
                self.assertEqual(error.name, expected["error"]["name"])
                self.assertEqual(error.value, expected["error"]["code"])
                checked += 1
        self.assertGreater(checked, 0)

    def test_every_event_matches_canonical_json(self) -> None:
        checked = 0
        for vector in load_vectors():
            for index, encoded in enumerate(vector["eventsXdr"]):
                with self.subTest(vector=vector["name"], event=index):
                    expected = vector["expected"]["events"][index]
                    event = decode_stream_pay_event(encoded, expected["contract"])
                    self.assertIsNotNone(event)
                    self.assertEqual(event.to_dict(), expected)
                    checked += 1
        self.assertGreaterEqual(checked, 37)

    def test_argument_builders_cover_bool_option_and_empty_arguments(self) -> None:
        args = streampay.resolve_time_args(1, False)
        self.assertEqual(args[1], ScVal("bool", False).to_xdr())
        self.assertEqual(streampay.get_stream_policy_args(None), [ScVal("void", None).to_xdr()])
        self.assertEqual(streampay.total_streams_args(), [])
        with self.assertRaises(streampay.EncodeError):
            streampay.resolve_time_args(1, 1)

    def test_empty_read_result_decodes_through_the_client(self) -> None:
        transport = FixtureTransport(ScVal("u64", 0).to_xdr())
        self.assertEqual(ReadClient(transport).total_streams(), 0)

    def test_contract_error_cannot_decode_as_a_successful_stream(self) -> None:
        vector = next(vector for vector in load_vectors() if vector["name"] == "error-not-active")
        with self.assertRaises(ContractError) as caught:
            streampay.decode_get_stream_result(vector["resultXdr"])
        self.assertEqual(caught.exception.code, 5)
        self.assertEqual(caught.exception.name, "StreamNotActive")
        self.assertIs(caught.exception.error, StreamError.StreamNotActive)


if __name__ == "__main__":
    unittest.main()
