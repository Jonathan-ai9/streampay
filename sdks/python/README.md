# StreamPay Python SDK

A typed, read-only StreamPay client generated from
[`../spec/streampay.spec.json`](../spec/streampay.spec.json). It uses only the
Python standard library at runtime and never signs or submits transactions.

## Install

From the repository root:

```bash
python -m pip install ./sdks/python
```

The package requires Python 3.10 or newer. To build a wheel without uploading it:

```bash
python -m pip wheel --no-deps --wheel-dir dist ./sdks/python
```

## Read client

Implement `ReadTransport.simulate(method, args)` with your Soroban RPC or test
harness. Arguments are raw ScVal XDR bytes; return the result as raw bytes or
base64 XDR. The SDK performs no network calls itself.

```python
from streampay import ReadClient, ReadTransport, Stream

class RpcTransport(ReadTransport):
    def simulate(self, method, args):
        return rpc.simulate_contract_call(method, args).result_xdr

client = ReadClient(RpcTransport())
stream: Stream = client.get_stream(1)
print(stream.to_dict())
```

Every spec operation marked `mutating: false` has a client method, a
`<method>_args` ScVal encoder and a `decode_<method>_result` decoder. Contract
errors raise `ContractError`; known errors expose the generated `StreamError`
enum through `error`, while unknown codes remain integers.

## Events

`decode_stream_pay_event(xdr, contract_id)` decodes all spec events into frozen
dataclasses. It returns `None` for another contract, a non-contract event, or an
unknown topic. A malformed StreamPay event raises `DecodeError` rather than
being silently ignored.

```python
from streampay import decode_stream_pay_event

event = decode_stream_pay_event(event_xdr, "C...")
if event is not None:
    print(event.to_dict())
```

Canonical dictionaries use decimal strings for integers, preserving values
such as `u128` deposits without precision loss.

## Verify

```bash
python -m unittest discover -s sdks/python/tests -v
make -C sdks check
```

Tests cover the shared result, error, argument and event vectors, plus malformed
XDR, numeric bounds, checksums, optional fields and unknown error/event cases.
Do not edit `src/streampay/_generated.py`; regenerate it with
`python sdks/generator/generate.py`.
