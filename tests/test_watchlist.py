import csv
import io

import watchlist as wl

A = {"title": "Arrival", "year": 2016, "genre": "Sci-Fi", "match_score": 90,
     "description": "d", "why_recommended": "w"}
B = {**A, "title": "Contact", "year": 1997}


def test_add_is_idempotent_and_case_insensitive():
    items = wl.add([], A)
    items = wl.add(items, {**A, "title": "arrival"})
    assert len(items) == 1 and wl.contains(items, A)


def test_remove_and_export():
    items = wl.add(wl.add([], A), B)
    items = wl.remove(items, A)
    rows = list(csv.DictReader(io.StringIO(wl.to_csv(items))))
    assert [r["title"] for r in rows] == ["Contact"]
    assert rows[0]["year"] == "1997"
