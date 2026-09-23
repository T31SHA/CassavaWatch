"""Fetch a balanced subsample of iCassava 2019 without downloading the 1.35 GB zip.

This is the same archive TFDS `cassava` is built from. We read the zip central
directory via HTTP Range requests, then range-fetch only the chosen members
(one request per image, parallel). Output: data/icassava/{train,test}/{class}/*.jpg

Usage: python ml/fetch_icassava.py [per_class_train] [per_class_test]
"""
import io
import random
import struct
import sys
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

URL = "https://storage.googleapis.com/emcassavadata/cassavaleafdata.zip"
OUT = Path(__file__).resolve().parent.parent / "data" / "icassava"
CLASSES = ["cbb", "cbsd", "cgm", "cmd", "healthy"]


def get_range(start, end):
    req = urllib.request.Request(URL, headers={"Range": f"bytes={start}-{end}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise


class HTTPFile(io.RawIOBase):
    """Minimal seekable read-only file over HTTP Range (for the central directory)."""

    def __init__(self):
        with urllib.request.urlopen(urllib.request.Request(URL, method="HEAD"), timeout=60) as r:
            self.size = int(r.headers["Content-Length"])
        self.pos = 0
        self.cache_start = self.size - 3_000_000  # central directory lives at the end
        self.cache = get_range(self.cache_start, self.size - 1)

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if self.pos >= self.cache_start:
            b = self.cache[self.pos - self.cache_start:self.pos - self.cache_start + n]
        else:
            b = get_range(self.pos, min(self.size, self.pos + n) - 1)
        self.pos += len(b)
        return b


def fetch_member(info, dest):
    if dest.exists():
        return
    start = info.header_offset
    blob = get_range(start, start + 30 + len(info.filename.encode()) + 1024 + info.compress_size)
    n_name, n_extra = struct.unpack("<HH", blob[26:30])
    data = blob[30 + n_name + n_extra: 30 + n_name + n_extra + info.compress_size]
    if info.compress_type == zipfile.ZIP_DEFLATED:
        data = zlib.decompress(data, -15)
    tmp = dest.with_suffix(".part")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    tmp.rename(dest)


def main(per_train=300, per_test=100):
    zf = zipfile.ZipFile(HTTPFile())
    members = {}
    for i in zf.infolist():
        parts = i.filename.lower().split("/")
        if i.is_dir() or not parts[-1].endswith((".jpg", ".jpeg", ".png")) or len(parts) < 3:
            continue
        split, cls = parts[-3], parts[-2]
        if cls in CLASSES and split in ("train", "test", "validation"):
            members.setdefault((split, cls), []).append(i)
    print({f"{k[0]}/{k[1]}": len(v) for k, v in sorted(members.items())}, flush=True)
    rng = random.Random(0)
    jobs = []
    for (split, cls), infos in members.items():
        want = {"train": per_train, "test": per_test}.get(split, 0)
        for i in rng.sample(infos, min(want, len(infos))):
            jobs.append((i, OUT / split / cls / Path(i.filename).name))
    rng.shuffle(jobs)  # interleave classes so a partial fetch is still balanced
    total = sum(j[0].compress_size for j in jobs)
    print(f"fetching {len(jobs)} images, {total / 1e6:.0f} MB", flush=True)
    done = 0
    with ThreadPoolExecutor(16) as ex:
        for _ in ex.map(lambda j: fetch_member(*j), jobs):
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)
    print(f"done -> {OUT}", flush=True)


if __name__ == "__main__":
    main(*[int(x) for x in sys.argv[1:3]])
