"""Benchmark signing service (PRD §14 langkah 14, AC-12/AC-13/AC-14, §15 NFR).

Mengukur dengan time.perf_counter_ns():
- AC-12: 30x operasi sign  -> n, min, max, mean, median, stddev
- AC-13: 30x operasi verify -> sama
- Diukur dua level (sesuai NFR §15): raw RSA-PSS (<100ms) dan full PDF (<3s).
- AC-14: tiga angka TERPISAH — raw signature (byte), public key DER/PEM
  (byte), penuh /Contents (byte).

Pemakaian (dari root repo, venv signer aktif):
    services\\signer\\.venv\\Scripts\\python.exe scripts\\benchmark.py [--n 30]

Output: tabel stdout + scripts/benchmark_results.json ( artifacts laporan,
boleh di-commit — tanpa secret).
"""

import argparse
import json
import statistics
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "signer"))

from app.crypto import rsa  # noqa: E402
from app.pdf import signer as pdf_signer  # noqa: E402
from app.verification import verify as verify_mod  # noqa: E402

NFR_RAW_MS = 100.0
NFR_FULL_S = 3.0
FIELD = {"page": 0, "x": 100, "y": 100, "width": 180, "height": 80}


def sample_pdf(pages: int = 1) -> bytes:
    """PDF minimal valid (salinan helper test; tanpa dependensi baru)."""
    out = [b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"]
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(pages))
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode(),
    }
    for i in range(pages):
        content = b"BT /F1 12 Tf 72 720 Td (SecureSign benchmark) Tj ET"
        cnum = 4 + 2 * i
        objs[3 + 2 * i] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            "/Resources << /Font << /F1 << /Type /Font "
            "/Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/Contents {cnum} 0 R >>"
        ).encode()
        objs[cnum] = (
            f"<< /Length {len(content)} >>\nstream\n".encode()
            + content
            + b"\nendstream"
        )
    offsets = {}
    for num in sorted(objs):
        offsets[num] = sum(len(x) for x in out)
        out.append(f"{num} 0 obj\n".encode() + objs[num] + b"\nendobj\n")
    startxref = sum(len(x) for x in out)
    n = max(objs) + 1
    out.append(f"xref\n0 {n}\n".encode())
    out.append(b"0000000000 65535 f \n")
    for i in range(1, n):
        out.append(f"{offsets[i]:010d} 00000 n \n".encode())
    out.append(
        f"trailer\n<< /Size {n} /Root 1 0 R >>\n"
        f"startxref\n{startxref}\n%%EOF".encode()
    )
    return b"".join(out)


def stats_ms(samples_ns: list) -> dict:
    ms = [ns / 1_000_000 for ns in samples_ns]
    return {
        "n": len(ms),
        "min_ms": round(min(ms), 3),
        "max_ms": round(max(ms), 3),
        "mean_ms": round(statistics.mean(ms), 3),
        "median_ms": round(statistics.median(ms), 3),
        "stddev_ms": round(statistics.stdev(ms), 3) if len(ms) > 1 else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    args = ap.parse_args()
    n = args.n
    if n < 2:
        print("n minimal 2 (butuh stddev)")
        return 2

    priv = rsa.generate_rsa_keypair()
    der = rsa.private_key_to_der(priv)
    pub = priv.public_key()
    pdf = sample_pdf()
    digest = b"byterange-digest-contoh-32-byte-0000"  # 32 byte

    # AC-12a: raw RSA-PSS sign.
    t = []
    sig_raw = b""
    for _ in range(n):
        s = time.perf_counter_ns()
        sig_raw = rsa.pss_sign(priv, digest)
        t.append(time.perf_counter_ns() - s)
    raw_sign = stats_ms(t)

    # Raw verify (pendukung AC-13).
    t = []
    for _ in range(n):
        s = time.perf_counter_ns()
        assert rsa.pss_verify(pub, sig_raw, digest)
        t.append(time.perf_counter_ns() - s)
    raw_verify = stats_ms(t)

    # AC-12b: full PDF signing.
    sign_kwargs = {
        "private_key_der": der,
        "signer_name": "Benchmark",
        "signer_position": "Sistem",
        "signer_institution": "SecureSign",
        "signed_at_iso": "2026-09-27T10:00:00Z",
        "verification_url": "https://securesign.example/verify/bench",
        **FIELD,
    }
    t = []
    signed = b""
    for i in range(n):
        s = time.perf_counter_ns()
        signed = pdf_signer.sign_pdf_visible(
            pdf, signature_id=str(uuid.uuid4()), **sign_kwargs
        )
        t.append(time.perf_counter_ns() - s)
    full_sign = stats_ms(t)

    # AC-13: full PDF verification.
    t = []
    for _ in range(n):
        s = time.perf_counter_ns()
        res = verify_mod.verify_pdf_signature(signed)
        assert res["valid"]
        t.append(time.perf_counter_ns() - s)
    full_verify = stats_ms(t)

    # AC-14: tiga angka terpisah.
    import re

    m = re.search(rb"/Contents\s*<([0-9A-Fa-f]+)>", signed)
    contents_bytes = len(m.group(1)) // 2 if m else 0
    pem = rsa.public_key_to_pem(priv)
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    spki_der = pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    sizes = {
        "raw_rsa_pss_signature_bytes": len(sig_raw),
        "public_key_der_bytes": len(spki_der),
        "public_key_pem_bytes": len(pem),
        "contents_bytes": contents_bytes,
    }

    report = {
        "raw_pss_sign": raw_sign,
        "raw_pss_verify": raw_verify,
        "full_pdf_sign": full_sign,
        "full_pdf_verify": full_verify,
        "sizes": sizes,
        "nfr": {
            "raw_below_100ms": raw_sign["mean_ms"] < NFR_RAW_MS
            and raw_verify["mean_ms"] < NFR_RAW_MS,
            "full_below_3s": full_sign["mean_ms"] < NFR_FULL_S * 1000
            and full_verify["mean_ms"] < NFR_FULL_S * 1000,
        },
    }

    def row(name, s, limit):
        flag = "PASS" if s["mean_ms"] < limit else "FAIL"
        print(
            f"{name:18s} n={s['n']:3d} min={s['min_ms']:9.3f} max={s['max_ms']:9.3f} "
            f"mean={s['mean_ms']:9.3f} median={s['median_ms']:9.3f} "
            f"stddev={s['stddev_ms']:8.3f} ms  [{flag}]"
        )

    print("== SecureSign benchmark (ms) ==")
    row("raw_pss_sign", raw_sign, NFR_RAW_MS)
    row("raw_pss_verify", raw_verify, NFR_RAW_MS)
    row("full_pdf_sign", full_sign, NFR_FULL_S * 1000)
    row("full_pdf_verify", full_verify, NFR_FULL_S * 1000)
    print("== sizes (bytes, AC-14) ==")
    for k, v in sizes.items():
        print(f"{k:28s} {v}")

    out_path = ROOT / "scripts" / "benchmark_results.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"laporan: {out_path}")
    return 0 if all(report["nfr"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
