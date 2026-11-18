from hashlib import sha256
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import PurePosixPath
import subprocess
import sys
from threading import BoundedSemaphore

import cv2
from fastapi import HTTPException
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend import db
from backend.demo import new_id
from backend.schemas import Finding
from backend.uploads import MAX_BYTES

cv2.setNumThreads(1)
workers = BoundedSemaphore(2)
PUBLIC = (db.assets.c.id, db.assets.c.name, db.assets.c.width, db.assets.c.height)
MAX_LOGOS = 6


@contextmanager
def processing_slot():
    if not workers.acquire(blocking=False):
        raise HTTPException(503, "Image processing is busy. Retry shortly.", headers={"Retry-After": "3"})
    try:
        yield
    finally:
        workers.release()


def decode(payload, kind):
    try:
        with Image.open(BytesIO(payload), formats=["PNG", "JPEG"]) as source:
            if source.width * source.height > 12_000_000 or getattr(source, "n_frames", 1) != 1:
                raise HTTPException(422, "Use a single image of at most 12 megapixels.")
            fmt = source.format
            image = ImageOps.exif_transpose(source).convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "The file could not be decoded as a PNG or JPEG.") from None
    if kind == "logo":
        bounds = image.getbbox()
        if not bounds:
            raise HTTPException(422, "The logo is completely transparent.")
        image = image.crop(bounds)
        image.thumbnail((512, 512))
        if min(image.size) < 8:
            raise HTTPException(422, "The logo needs at least 8 visible pixels on each side.")
    else:
        # A single orientation and matte keep review coordinates aligned in every browser.
        matte = Image.new("RGB", image.size, "white")
        matte.paste(image, mask=image.getchannel("A"))
        image = matte
    buf = BytesIO()
    if fmt == "JPEG":
        image = image.convert("RGB")
    image.save(buf, format=fmt, quality=96)
    lines = []
    if kind == "artwork":
        sample = image.copy()
        sample.thumbnail((2200, 2200))
        input_image = BytesIO()
        sample.save(input_image, format="PNG")
        try:
            proc = subprocess.run([sys.executable, "-m", "backend.ocr"], input=input_image.getvalue(),
                                  capture_output=True, timeout=35, check=True)
            lines = json.loads(proc.stdout)
        except (subprocess.SubprocessError, OSError, ValueError):
            raise HTTPException(503, "OCR is unavailable. Check the English language data and retry.") from None
        if sum(len(word["text"]) + 1 for line in lines for word in line) > 20000:
            raise HTTPException(422, "Artwork text exceeds 20,000 characters.")
    return dict(image=buf.getvalue(), mime="image/png" if fmt == "PNG" else "image/jpeg",
                width=image.width, height=image.height, lines=lines)


def save_upload(actor, upload, kind):
    name = PurePosixPath((upload.filename or "").replace(chr(92), "/")).name
    if PurePosixPath(name).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(415, "Upload a PNG or JPEG image.")
    payload = upload.file.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, "The file exceeds the 5 MB limit.")
    digest = sha256(payload).hexdigest()
    match = (db.assets.c.workspace_id == actor.workspace_id, db.assets.c.kind == kind, db.assets.c.digest == digest)
    with db.engine.connect() as conn:
        existing = conn.execute(select(*PUBLIC).where(*match, db.assets.c.active.is_(True))).mappings().first()
        if existing:
            return existing
    with processing_slot():
        values = decode(payload, kind)
    try:
        with db.engine.begin() as conn:
            if kind == "logo":
                # Serialise logo-set changes per workspace, including reactivation.
                bump_logos(conn, actor)
                if len(logos(conn, actor)) >= MAX_LOGOS:
                    raise HTTPException(409, "Retire an approved logo before adding another.")
            row = conn.execute(select(*PUBLIC, db.assets.c.active).where(*match)).mappings().first()
            if row:
                conn.execute(db.assets.update().where(*match).values(active=True))
                return {c.name: row[c.name] for c in PUBLIC}
            return conn.execute(db.assets.insert().values(id=new_id(), workspace_id=actor.workspace_id,
                name=name[:160], kind=kind, digest=digest, active=True, **values).returning(*PUBLIC)).mappings().one()
    except IntegrityError:
        with db.engine.connect() as conn:
            return conn.execute(select(*PUBLIC).where(*match)).mappings().one()


def logos(conn, actor, include_pixels=False):
    cols = (*PUBLIC, db.assets.c.image) if include_pixels else PUBLIC
    return conn.execute(select(*cols).where(db.assets.c.workspace_id == actor.workspace_id,
        db.assets.c.kind == "logo", db.assets.c.active.is_(True)).order_by(db.assets.c.created_at)).mappings().all()


def bump_logos(conn, actor):
    conn.execute(db.workspaces.update().where(db.workspaces.c.id == actor.workspace_id)
                 .values(logo_version=db.workspaces.c.logo_version + 1))


def text_evidence(lines):
    words, spans, offset = [], [], 0
    for line in lines:
        for word in line:
            value = word["text"]
            words.append(value)
            spans.append((offset, offset + len(value), word["box"]))
            offset += len(value) + 1
    return " ".join(words), spans


def visual_finding(check, category, explanation, regions=(), supported=False):
    return Finding(category=category, severity="low" if supported else "medium",
                   origin="artwork", original_text="", suggested_correction="",
                   explanation=explanation, evidence_status="SUPPORTED" if supported else "NEEDS_HUMAN_REVIEW",
                   requires_human_review=not supported, policy_key=check["id"], rule_title=check["title"],
                   rule_version=check["version"], regions=list(regions))


def locate_logos(canvas, reference):
    rgba = np.array(Image.open(BytesIO(reference["image"])).convert("RGBA"))
    # Compare edges to locate the mark, then compare its visible colours at the candidate location.
    ref = rgba[:, :, :3].copy()
    mask = rgba[:, :, 3] > 180
    if not mask.any():
        return []
    # Use a contrasting matte to retain the silhouette of white transparent marks.
    ref[~mask] = 0 if np.mean(ref[mask]) > 160 else 255
    edge_canvas = cv2.Canny(cv2.cvtColor(canvas, cv2.COLOR_RGB2GRAY), 40, 100)
    height, width = canvas.shape[:2]
    candidates = []
    widths = sorted(set([ref.shape[1]] + [int(x) for x in np.geomspace(16, width, 35)]))
    for w in widths:
        h = round(w * ref.shape[0] / ref.shape[1])
        if not (8 <= h <= height and 8 <= w <= width):
            continue
        template = cv2.resize(ref, (w, h), interpolation=cv2.INTER_AREA)
        edges = cv2.Canny(cv2.cvtColor(template, cv2.COLOR_RGB2GRAY), 40, 100)
        if np.count_nonzero(edges) < 8:
            continue
        score_map = cv2.matchTemplate(edge_canvas, edges, cv2.TM_CCORR_NORMED)
        for _ in range(4):
            _, score, _, (x, y) = cv2.minMaxLoc(score_map)
            if score < .40:
                break
            score_map[max(0, y-h//2):y+h//2+1, max(0, x-w//2):x+w//2+1] = 0
            opaque = cv2.resize(mask.astype("uint8"), (w, h)).astype(bool)
            if not opaque.any():
                continue
            # Opaque logo files often include a large, uniform white margin.
            # Keep it from drowning out a colour change within the actual mark.
            background = template[0, 0].astype(float)
            corners = template[[0, 0, -1, -1], [0, -1, 0, -1]].astype(float)
            if mask.all() and np.abs(corners - background).max() < 12:
                foreground = opaque & (np.abs(template.astype(float) - background).max(axis=2) > 24)
                if foreground.sum() >= 8:
                    opaque = foreground
            diff = np.abs(canvas[y:y+h, x:x+w].astype(float) - template)
            candidates.append((score, float(diff[opaque].mean()), [x/width, y/height, (x+w)/width, (y+h)/height]))
    return candidates


def overlaps(a, b):
    common = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    smaller = min((r[2]-r[0])*(r[3]-r[1]) for r in (a,b))
    return common > .5 * smaller


def palette_issues(canvas, colors, check):
    h, w = canvas.shape[:2]
    small = cv2.resize(canvas, (max(1, round(180*w/max(h,w))), max(1, round(180*h/max(h,w)))),
                       interpolation=cv2.INTER_AREA)
    approved = np.uint8([[list(bytes.fromhex(color[1:])) for color in colors]])
    lab = cv2.cvtColor(small.astype("float32") / 255, cv2.COLOR_RGB2Lab)
    refs = cv2.cvtColor(approved.astype("float32") / 255, cv2.COLOR_RGB2Lab)[0]
    distant = np.minimum.reduce([np.linalg.norm(lab - ref, axis=2) for ref in refs]) > 27
    saturated = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)[:, :, 1] > 64
    _, labels, stats, _ = cv2.connectedComponentsWithStats(np.uint8(distant & saturated))
    sh, sw = labels.shape
    issues = []
    for i in sorted(range(1, len(stats)), key=lambda idx: -stats[idx, 4])[:4]:
        x, y, width, height, area = map(int, stats[i])
        if area < 0.03 * sw * sh:
            break
        color = "#%02X%02X%02X" % tuple(np.median(small[labels == i], axis=0).astype(int))
        issues.append(visual_finding(check, "Brand colours",
            f"Check the {color} region against the approved palette ({', '.join(colors)}).",
            [[x/sw, y/sh, (x+width)/sw, (y+height)/sh]]))
    return issues


def visual_review(asset, references, workspace):
    image = Image.open(BytesIO(asset["image"])).convert("RGB")
    image.thumbnail((800, 800))
    canvas = np.array(image)
    profile = workspace.profile
    palette = dict(id="visual:palette", version=workspace.palette_version, title="Approved brand colours",
                   colors=[profile["primary_color"], profile["secondary_color"]])
    checks = [palette]
    issues = palette_issues(canvas, palette["colors"], palette)
    if references:
        logo = dict(id="visual:logo", version=workspace.logo_version, title="Approved logo variants",
                    references=[{"id": r["id"], "name": r["name"]} for r in references])
        checks.append(logo)
        matches = [(score >= .57 and difference < 28, score, box, ref["name"])
                   for ref in references for score, difference, box in locate_logos(canvas, ref)]
        marked = []
        for verified, score, box, name in sorted(matches, key=lambda m: (m[0], m[1]), reverse=True):
            if any(overlaps(box, prior) for prior in marked) or (marked and score < .65):
                continue
            marked.append(box)
            message = (f"Matched approved logo {name}." if verified else
                       f"A possible logo differs from the approved reference {name}. Check this region.")
            issues.append(visual_finding(logo, "Brand logo", message, [box], supported=verified))
            if len(marked) == 8:
                break
        if not marked:
            issues.append(visual_finding(logo, "Brand logo",
                "An approved logo could not be located reliably. Check the placement and mark against " +
                ", ".join(ref["name"] for ref in references) + "."))
    return issues, checks
